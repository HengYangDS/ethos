"""The patch workspace is a repository of its own and reports what Git does with a patch."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.patch_workspace as owner
import ethos.adapters.repo.git_patch as reader
from ethos.adapters.repo.git_patch import unified_patch_changes
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_EDIT = "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n"
_RENAME = "diff --git a/a.txt b/b.txt\nsimilarity index 100%\nrename from a.txt\nrename to b.txt\n"
_COPY = "diff --git a/a.txt b/c.txt\nsimilarity index 100%\ncopy from a.txt\ncopy to c.txt\n"
_MOVE_AND_REFILL = _RENAME + (
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
_EXECUTABLE = "diff --git a/tool.sh b/tool.sh\nold mode 100644\nnew mode 100755\n"
# Git writes no `---` and `+++` lines for an entry without content.
_EMPTY_DELETED = "diff --git a/empty.txt b/empty.txt\ndeleted file mode 100644\n"
_EMPTY_CREATED = "diff --git a/fresh.txt b/fresh.txt\nnew file mode 100644\n"
# An added line of text that begins like a header of the next file.
_MARKED_LINE = (
    "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1,2 @@\n old\n+++ b/tool.sh\n"
    "diff --git a/tool.sh b/tool.sh\n--- a/tool.sh\n+++ b/tool.sh\n@@ -1 +1,2 @@\n"
    " #!/bin/sh\n+more\n"
)
# Text after an entry without hunks: Git ended the entry's header at the empty line.
_TEXT_AFTER = _EMPTY_CREATED + "\n--- a/a.txt\n+++ /dev/null\n"
# A deletion written without its `deleted file mode` line, as a plain unified diff has it.
_DELETE_WITHOUT_MODE = (
    "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n"
)
_NEW_LINK = (
    "diff --git a/link b/link\nnew file mode 120000\n--- /dev/null\n+++ b/link\n"
    "@@ -0,0 +1 @@\n+no-such-target\n\\ No newline at end of file\n"
)
_NEW_SUBMODULE = (
    "diff --git a/vendor b/vendor\nnew file mode 160000\n--- /dev/null\n+++ b/vendor\n"
    "@@ -0,0 +1 @@\n+Subproject commit 1111111111111111111111111111111111111111\n"
)
# The same link with its mode where Git still reads it, and one mode line without its pair.
_LINK_MODE_LATER = (
    "diff --git a/link b/link\n--- /dev/null\n+++ b/link\nnew file mode 120000\n"
    "@@ -0,0 +1 @@\n+a.txt\n\\ No newline at end of file\n"
)
_LINK_MODE_RETURN = _NEW_LINK.replace("new file mode 120000\n", "new file mode 120000\r\n")
_LONE_LINK_MODE = "diff --git a/a.txt b/a.txt\nnew mode 120000\n"
# What each patch of regular files leaves at every path that it changes, and its effect there.
_READ = {
    "edit": (_EDIT, {"a.txt": ("new\n", "modify")}),
    "prose-before": ("new mode for the scripts\n\n" + _EDIT, {"a.txt": ("new\n", "modify")}),
    # A move is the deletion of its source and the creation of its target.
    "rename": (_RENAME, {"a.txt": (None, "delete"), "b.txt": ("old\n", "create")}),
    "copy": (_COPY, {"c.txt": ("old\n", "create")}),
    # The refilled path holds its bytes as before, so Git reports no change of it.
    "move-and-refill": (
        _MOVE_AND_REFILL,
        {"a.txt": ("old\n", "modify"), "b.txt": ("old\n", "create")},
    ),
    "file-to-directory": (
        _FILE_TO_DIRECTORY,
        {"a.txt": (None, "delete"), "a.txt/b.txt": ("new\n", "create")},
    ),
    "swap": (_SWAP, {"a.txt": ("#!/bin/sh\n", "modify"), "tool.sh": ("old\n", "modify")}),
    "executable": (_EXECUTABLE, {"tool.sh": ("#!/bin/sh\n", "modify")}),
    "empty-deleted": (_EMPTY_DELETED, {"empty.txt": (None, "delete")}),
    "empty-created": (_EMPTY_CREATED, {"fresh.txt": ("", "create")}),
    "line-like-a-header": (
        _MARKED_LINE,
        {"a.txt": ("old\n++ b/tool.sh\n", "modify"), "tool.sh": ("#!/bin/sh\nmore\n", "modify")},
    ),
    "text-after-an-entry": (_TEXT_AFTER, {"fresh.txt": ("", "create")}),
    "deletion-without-its-mode": (_DELETE_WITHOUT_MODE, {"a.txt": (None, "delete")}),
}


def _repository(tmp_path: Path) -> Path:
    repo = init_git_repo(tmp_path / "repo")
    (repo / "a.txt").write_text("old\n", encoding="utf-8")
    (repo / "tool.sh").write_text("#!/bin/sh\n", encoding="utf-8")
    (repo / "empty.txt").write_text("", encoding="utf-8")
    commit_fixture(repo, "record three files")
    return repo


def _entered(repo: Path, patch: str) -> dict[str, tuple[str | None, str]]:
    """Enter the workspace of one patch; return each changed path's text and effect."""
    changes, gap = unified_patch_changes(repo, patch)
    assert (gap, bool(changes)) == ("", True)
    with owner.patched_workspace(repo, patch, changes) as (_workspace, postimages, effects):
        assert postimages.keys() == effects.keys()
        return {path: (text, effects[path]) for path, text in postimages.items()}


@pytest.mark.parametrize("shape", list(_READ))
@pytest.mark.parametrize("inside", ["", "build", f"build{os.pathsep}1"])
def test_a_patch_of_regular_files_is_read_wherever_the_workspace_lies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shape: str, inside: str
) -> None:
    """Inside another checkout a plain directory is part of that work tree, and Git skips.

    There Git exits with 0 and changes nothing, also where the directory's name holds the
    separator of a path list. The workspace is a repository of its own, so no path lies
    outside it, and its own index tells what the patch did at each path.
    """
    repo = _repository(tmp_path)
    if inside:
        directory = init_git_repo(tmp_path / "other") / inside
        directory.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(directory))
    patch, expected = _READ[shape]
    assert _entered(repo, patch) == expected


@pytest.mark.parametrize(
    ("patch", "refusal"),
    [
        (_NEW_LINK, "no regular file"),
        (_NEW_SUBMODULE, "no regular file"),
        (_LINK_MODE_RETURN, "no regular file"),
        # Git refuses these two when it applies them; a Git that applied one records its mode.
        (_LINK_MODE_LATER, "application failed|no regular file"),
        (_LONE_LINK_MODE, "application failed|no regular file"),
    ],
    ids=["link", "submodule", "mode-with-a-return", "mode-after-the-file-lines", "lone-mode"],
)
def test_a_patch_that_makes_another_kind_of_entry_is_refused(
    tmp_path: Path, patch: str, refusal: str
) -> None:
    """The reader names the entry; the apply or the mode in the index refuses it."""
    repo = _repository(tmp_path)
    changes, gap = unified_patch_changes(repo, patch)
    assert gap == ""
    with (
        pytest.raises(ValueError, match=refusal),
        owner.patched_workspace(repo, patch, changes),
    ):
        pytest.fail("the workspace was yielded")


@pytest.mark.parametrize(
    ("command", "status", "output", "refusal"),
    [
        ("diff-tree", 0, b":100644 100644 a b M\0a.txt\0b.txt\0", "not of Git's form"),
        ("diff-tree", 0, b":100644 100644 a M\0a.txt\0", "not of Git's form"),
        ("diff-tree", 0, b":120000 100644 a b M\0a.txt\0", "no regular file"),
        ("write-tree", 1, b"", "workspace failed"),
    ],
    ids=["unpaired-path", "short-entry", "link-before", "failed-step"],
)
def test_a_record_that_is_not_of_git_s_form_is_refused(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    status: int,
    output: bytes,
    refusal: str,
) -> None:
    """The record is read strictly, and a step other than the apply fails by its own name."""
    real = owner.run_git

    def recorded(root: Path, *arguments: str, **options: object):
        done = real(root, *arguments, **options)
        if arguments[0] != command:
            return done
        return done.__class__(done.args, status, output, b"")

    monkeypatch.setattr(owner, "run_git", recorded)
    monkeypatch.setattr(reader, "run_git", recorded)
    repo = _repository(tmp_path)
    changes, _gap = unified_patch_changes(repo, _EDIT)
    with (
        pytest.raises(ValueError, match=refusal),
        owner.patched_workspace(repo, _EDIT, changes),
    ):
        pytest.fail("the workspace was yielded")


# The null target of `_DELETE_WITHOUT_MODE` with content left: Git writes it to `dev/null`.
_CONTENT_TO_THE_NULL_PATH = _DELETE_WITHOUT_MODE.replace(
    "@@ -1 +0,0 @@\n-old\n", "@@ -1 +1 @@\n-old\n+kept\n"
)
# A null target under a copy to the null path: Git empties a copy and deletes nothing.
_COPY_TO_THE_NULL_PATH = (
    "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ /dev/null\n"
    "copy from tool.sh\ncopy to dev/null\n@@ -1 +0,0 @@\n-#!/bin/sh\n"
)


_NEEDS_LINKS = pytest.mark.skipif(os.name == "nt", reason="symbolic links need a privilege")


@pytest.mark.parametrize(
    ("patch", "held"),
    [
        (_FILE_TO_DIRECTORY, ""),
        (_CONTENT_TO_THE_NULL_PATH, ""),
        (_COPY_TO_THE_NULL_PATH, ""),
        (_DELETE_WITHOUT_MODE, "file"),
        (_DELETE_WITHOUT_MODE, "directory"),
        (_DELETE_WITHOUT_MODE, "file-above"),
        (_DELETE_WITHOUT_MODE, "junction-above"),
        pytest.param(_DELETE_WITHOUT_MODE, "link", marks=_NEEDS_LINKS),
        pytest.param(_DELETE_WITHOUT_MODE, "link-above", marks=_NEEDS_LINKS),
    ],
    ids=[
        "an-entry-left-out",
        "content-at-the-null-path",
        "nothing-deleted",
        "a-file-at-the-null-path",
        "a-directory-at-the-null-path",
        "a-file-above-the-null-path",
        "a-junction-above-the-null-path",
        "a-link-at-the-null-path",
        "a-link-above-the-null-path",
    ],
)
def test_a_changed_path_that_no_change_names_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, patch: str, held: str
) -> None:
    """Every changed path is named or deleted; only Git's empty file at the null path is let be.

    That file is let be where the record shows the entry's preimage deleted and the name is
    free in the repository: nothing lies at it, and only directories lie above it.
    """
    repo = _repository(tmp_path)
    if held == "file-above":
        (repo / "dev").write_text("held\n", encoding="utf-8")
    elif held == "link-above":
        (tmp_path / "elsewhere").mkdir()
        (repo / "dev").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    elif held:
        (repo / "dev").mkdir()
    if held == "junction-above":
        # A junction reads as a directory and as no link; the product's own check names it.
        monkeypatch.setattr(owner, "is_junction", lambda place: place == repo / "dev")
    if held == "file":
        (repo / "dev/null").write_text("held\n", encoding="utf-8")
    elif held == "directory":
        (repo / "dev/null").mkdir()
    elif held == "link":
        (repo / "dev/null").symlink_to("nowhere")
    changes, gap = unified_patch_changes(repo, patch)
    assert gap == ""
    with (
        pytest.raises(ValueError, match="no change names"),
        owner.patched_workspace(repo, patch, changes[:1]),
    ):
        pytest.fail("the workspace was yielded")


def test_the_null_path_is_free_under_a_real_directory(tmp_path: Path) -> None:
    """A directory above the null path that holds other files leaves the name free."""
    repo = _repository(tmp_path)
    (repo / "dev").mkdir()
    (repo / "dev/other.txt").write_text("kept\n", encoding="utf-8")
    assert _entered(repo, _DELETE_WITHOUT_MODE) == {"a.txt": (None, "delete")}


@pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="a directory that its owner cannot search needs POSIX modes and no superuser",
)
def test_a_place_that_cannot_be_looked_at_is_no_absence(tmp_path: Path) -> None:
    """A directory above the null path that cannot be searched is an error, on every interpreter."""
    repo = _repository(tmp_path)
    (repo / "dev").mkdir()
    changes, _gap = unified_patch_changes(repo, _DELETE_WITHOUT_MODE)
    (repo / "dev").chmod(0)
    try:
        with (
            pytest.raises(PermissionError),
            owner.patched_workspace(repo, _DELETE_WITHOUT_MODE, changes),
        ):
            pytest.fail("the workspace was yielded")
    finally:
        (repo / "dev").chmod(0o755)


def test_a_path_in_the_workspace_s_own_git_directory_is_refused(tmp_path: Path) -> None:
    """No change may name the directory that makes the workspace a repository."""
    repo = _repository(tmp_path)
    change: dict[str, object] = {"old_path": "/dev/null", "path": ".git/x"}
    with (
        pytest.raises(ValueError, match="escapes root"),
        owner.patched_workspace(repo, "", [change]),
    ):
        pytest.fail("the workspace was yielded")


def test_a_named_path_without_its_file_must_be_a_deletion(tmp_path: Path) -> None:
    """A named path that the patch leaves absent is read as absent only where Git deleted it."""
    repo = _repository(tmp_path)
    changes, _gap = unified_patch_changes(repo, _EDIT)
    changes.append({"old_path": "/dev/null", "path": "c.txt"})
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
    change: dict[str, object] = {"old_path": "link", "path": "link"}
    with (
        pytest.raises(ValueError, match="no regular file"),
        owner.patched_workspace(repo, "", [change]),
    ):
        pytest.fail("the workspace was yielded")


def test_a_path_that_names_the_root_itself_is_refused(tmp_path: Path) -> None:
    """An empty path names no file under the root."""
    repo = _repository(tmp_path)
    change: dict[str, object] = {"old_path": ".", "path": "a.txt"}
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
    with owner.patched_workspace(repo, _EDIT, changes) as (workspace, postimages, _effects):
        assert not (workspace / ".git" / "marker").exists()
    assert postimages == {"a.txt": "new\n"}
