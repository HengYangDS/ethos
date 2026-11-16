"""The patch workspace is a repository of its own and reads regular files alone."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_workspace as owner
from ethos.adapters.repo.git_patch import unified_patch_changes
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_EDIT = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
_MOVE_AND_REFILL = (
    "diff --git a/a.txt b/b.txt\nsimilarity index 100%\nrename from a.txt\nrename to b.txt\n"
    "diff --git a/a.txt b/a.txt\nnew file mode 100644\n--- /dev/null\n+++ b/a.txt\n"
    "@@ -0,0 +1 @@\n+old\n"
)
_FILE_TO_DIRECTORY = (
    "diff --git a/a.txt b/a.txt\ndeleted file mode 100644\n--- a/a.txt\n+++ /dev/null\n"
    "@@ -1 +0,0 @@\n-old\n"
    "diff --git a/a.txt/b.txt b/a.txt/b.txt\nnew file mode 100644\n--- /dev/null\n"
    "+++ b/a.txt/b.txt\n@@ -0,0 +1 @@\n+new\n"
)
_SWAP = (
    "diff --git a/a.txt b/tool.sh\nsimilarity index 100%\nrename from a.txt\nrename to tool.sh\n"
    "diff --git a/tool.sh b/a.txt\nsimilarity index 100%\nrename from tool.sh\nrename to a.txt\n"
)
_NEW_LINK = (
    "diff --git a/link b/link\nnew file mode 120000\n--- /dev/null\n+++ b/link\n"
    "@@ -0,0 +1 @@\n+no-such-target\n\\ No newline at end of file\n"
)
_NEW_SUBMODULE = (
    "diff --git a/vendor b/vendor\nnew file mode 160000\n--- /dev/null\n+++ b/vendor\n"
    "@@ -0,0 +1 @@\n+Subproject commit 1111111111111111111111111111111111111111\n"
)
# What each patch of regular files leaves at the paths it names.
_READ = {
    _EDIT: {"a.txt": "new\n"},
    # The refilled path holds its bytes as before; the move's target holds them too.
    _MOVE_AND_REFILL: {"a.txt": "old\n", "b.txt": "old\n"},
    # Git tracks no directory: the deleted file's path reads as absent beside the new file.
    _FILE_TO_DIRECTORY: {"a.txt": None, "a.txt/b.txt": "new\n"},
    _SWAP: {"a.txt": "#!/bin/sh\n", "tool.sh": "old\n"},
}
_IDS = ["edit", "move-and-refill", "file-to-directory", "swap"]


def _repository(tmp_path: Path) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "a.txt").write_text("old\n", encoding="utf-8")
    (repo / "tool.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    commit_fixture(repo, "record two files")
    return repo


def _entered(repo: Path, patch: str) -> dict[str, str | None]:
    """Enter the workspace of one patch and return what it reads at each named path."""
    changes, gap = unified_patch_changes(repo, patch)
    assert (gap, bool(changes)) == ("", True)
    with owner.patched_workspace(repo, patch, changes) as (_workspace, postimages):
        return postimages


@pytest.mark.parametrize("patch", list(_READ), ids=_IDS)
@pytest.mark.parametrize("inside", ["", "build", f"build{os.pathsep}1"])
def test_a_patch_of_regular_files_is_read_wherever_the_workspace_lies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, patch: str, inside: str
) -> None:
    """Inside another checkout a plain directory is part of that work tree, and Git skips.

    There Git exits with 0 and changes nothing, also where the directory's name holds the
    separator of a path list. The workspace is a repository of its own, so no path lies
    outside it and each named path reads as the patch leaves it.
    """
    repo = _repository(tmp_path)
    if inside:
        directory = init_git_repo(tmp_path / "other") / inside
        directory.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(directory))
    assert _entered(repo, patch) == _READ[patch]


@pytest.mark.parametrize("patch", [_NEW_LINK, _NEW_SUBMODULE], ids=["link", "submodule"])
def test_a_patch_that_declares_another_kind_of_entry_is_refused(tmp_path: Path, patch: str) -> None:
    """The patch's own mode decides, whatever the workspace's Git would write for it."""
    with pytest.raises(ValueError, match="no regular file"):
        _entered(_repository(tmp_path), patch)


def test_a_path_in_the_workspace_s_own_git_directory_is_refused(tmp_path: Path) -> None:
    """No change may name the directory that makes the workspace a repository."""
    repo = _repository(tmp_path)
    change: dict[str, object] = {"old_path": "/dev/null", "path": ".git/x", "new": True}
    with (
        pytest.raises(ValueError, match="escapes root"),
        owner.patched_workspace(repo, "", [change]),
    ):
        pytest.fail("the workspace was yielded")


def test_text_around_the_entries_declares_no_mode(tmp_path: Path) -> None:
    """Only an entry's header declares a mode; a line of prose before the entries does not."""
    assert _entered(_repository(tmp_path), "new mode for the scripts\n\n" + _EDIT) == _READ[_EDIT]


def test_a_mode_change_between_regular_files_is_read(tmp_path: Path) -> None:
    """Making a file executable keeps it a regular file, so the patch is read as usual."""
    patch = "diff --git a/tool.sh b/tool.sh\nold mode 100644\nnew mode 100755\n"
    assert _entered(_repository(tmp_path), patch) == {"tool.sh": "#!/bin/sh\n"}


def test_a_named_path_without_its_file_must_be_a_deletion(tmp_path: Path) -> None:
    """A named path that the patch leaves absent is read as absent only where it is deleted."""
    repo = _repository(tmp_path)
    changes, _gap = unified_patch_changes(repo, _EDIT)
    changes.append({"old_path": "/dev/null", "path": "c.txt", "new": True, "deleted": False})
    with (
        pytest.raises(ValueError, match="without its file"),
        owner.patched_workspace(repo, _EDIT, changes),
    ):
        pytest.fail("the workspace was yielded")


@pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege on Windows")
def test_a_preimage_that_is_no_regular_file_is_refused(tmp_path: Path) -> None:
    """The workspace copies regular files alone; a link's text is not what it names."""
    repo = _repository(tmp_path)
    (repo / "link").symlink_to("a.txt")
    change: dict[str, object] = {"old_path": "link", "path": "link", "deleted": False}
    with (
        pytest.raises(ValueError, match="no regular file"),
        owner.patched_workspace(repo, "", [change]),
    ):
        pytest.fail("the workspace was yielded")


def test_a_path_that_names_the_root_itself_is_refused(tmp_path: Path) -> None:
    """An empty path names no file under the root."""
    repo = _repository(tmp_path)
    change: dict[str, object] = {"old_path": ".", "path": "a.txt", "deleted": False}
    with (
        pytest.raises(ValueError, match="escapes root"),
        owner.patched_workspace(repo, "", [change]),
    ):
        pytest.fail("the workspace was yielded")


def test_the_workspace_takes_nothing_from_a_git_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The host's template does not reach the workspace, whatever it holds."""
    template = tmp_path / "template"
    template.mkdir()
    (template / "marker").write_text("from the template\n", encoding="utf-8")
    count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    monkeypatch.setenv(f"GIT_CONFIG_KEY_{count}", "init.templateDir")
    monkeypatch.setenv(f"GIT_CONFIG_VALUE_{count}", template.as_posix())
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(count + 1))
    repo = _repository(tmp_path)
    changes, _gap = unified_patch_changes(repo, _EDIT)
    with owner.patched_workspace(repo, _EDIT, changes) as (workspace, postimages):
        assert not (workspace / ".git" / "marker").exists()
    assert postimages == _READ[_EDIT]
