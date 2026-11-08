"""A built patch applies with `git apply` to exactly each postimage and skips unchanged paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_patch import unified_patch
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
