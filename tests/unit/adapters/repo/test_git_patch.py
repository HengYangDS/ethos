"""A built patch applies to exactly each postimage, and a read patch names what Git names."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_patch import unified_patch
from ethos.adapters.repo.git_patch import unified_patch_changes
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_a_built_patch_applies_to_each_postimage(tmp_path: Path) -> None:
    """An unchanged pair adds nothing; a missing final newline and a non-ASCII path survive."""
    repo = init_git_repo(tmp_path / "repo")
    changes = [
        ("kept.md", b"kept\n", b"kept\n"),
        ("docs/notes.md", b"one\ntwo\n", b"one\n2"),
        ("docs/café.md", "café\n".encode(), "café au lait\n".encode()),
    ]
    for path, before, _after in changes:
        (repo / path).parent.mkdir(parents=True, exist_ok=True)
        (repo / path).write_bytes(before)

    patch = unified_patch(changes)
    run_git(repo, "apply", "--whitespace=nowarn", "-", stdin=patch.encode(), text=False)

    assert "kept.md" not in patch
    assert [(repo / path).read_bytes() for path, _before, _after in changes] == [
        after for _path, _before, after in changes
    ]


_CREATED = "diff --git a/fresh.txt b/fresh.txt\nnew file mode 100644\n"
_READ = {
    "edit": (
        "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n",
        [("a.txt", "a.txt")],
    ),
    "rename": (
        "diff --git a/a.txt b/b.txt\nsimilarity index 100%\nrename from a.txt\nrename to b.txt\n",
        [("a.txt", "b.txt")],
    ),
    # Git reads `rename old` and `rename new` as it reads `rename from` and `rename to`.
    "rename-in-the-older-words": (
        "diff --git a/a.txt b/b.txt\nsimilarity index 100%\nrename old a.txt\nrename new b.txt\n",
        [("a.txt", "b.txt")],
    ),
    "copy": (
        "diff --git a/a.txt b/c.txt\nsimilarity index 100%\ncopy from a.txt\ncopy to c.txt\n",
        [("a.txt", "c.txt")],
    ),
    # Git writes no `---` and `+++` lines for an entry without content.
    "empty-created": (_CREATED, [("/dev/null", "fresh.txt")]),
    "empty-deleted": (
        "diff --git a/empty.txt b/empty.txt\ndeleted file mode 100644\n",
        [("empty.txt", "empty.txt")],
    ),
    # Git ended the entry's header at the empty line; the lines after it belong to no entry.
    "text-after-an-entry": (
        _CREATED + "\n--- a/a.txt\n+++ /dev/null\n",
        [("/dev/null", "fresh.txt")],
    ),
    # Git reports the null path for a deletion without its mode line; the preimage names it.
    "deletion-without-its-mode": (
        "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ /dev/null\n@@ -1 +0,0 @@\n-old\n",
        [("a.txt", "a.txt")],
    ),
    # A line of content that begins like a header moves no path.
    "line-like-a-header": (
        "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1,2 @@\n old\n+++ b/c.txt\n",
        [("a.txt", "a.txt")],
    ),
}


@pytest.mark.parametrize("shape", list(_READ))
def test_each_entry_names_git_s_path_and_where_its_preimage_lies(
    tmp_path: Path, shape: str
) -> None:
    """The entry's path is the one that Git reports; the text is read for the preimage alone."""
    patch, expected = _READ[shape]
    changes, gap = unified_patch_changes(init_git_repo(tmp_path / "repo"), patch)
    assert (gap, [(change["old_path"], change["path"]) for change in changes]) == ("", expected)
    assert all(change.keys() == {"old_path", "path"} for change in changes)
