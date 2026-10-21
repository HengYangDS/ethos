"""Native Git attribute observations of tracked paths."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.repo.git_attributes as git_attributes
from ethos.adapters.repo.git_attributes import checkout_line_endings
from ethos.adapters.repo.git_attributes import received_paths
from ethos.adapters.repo.git_attributes import text_paths
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def test_received_paths_follow_native_linguist_attributes(tmp_path: Path) -> None:
    """Vendored and generated paths are received; an unset attribute keeps a path authored."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".gitattributes").write_text(
        "* text=auto eol=lf\n"
        "assets/fonts/** linguist-vendored\n"
        "dist/** linguist-generated=true\n"
        "assets/fonts/Authored.md -linguist-vendored\n",
        encoding="utf-8",
    )
    paths = (
        "assets/fonts/OFL.txt",
        "dist/index_bg.wasm",
        "assets/fonts/Authored.md",
        'docs/über "quoted".md',
    )
    assert received_paths(repo, paths) == {"assets/fonts/OFL.txt", "dist/index_bg.wasm"}
    assert received_paths(repo, ()) == frozenset()


def test_checkout_line_endings_follow_later_and_nested_patterns(tmp_path: Path) -> None:
    """Each path's text and eol are what native Git resolves, overrides and nesting included."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".gitattributes").write_text(
        "* text=auto eol=lf\nrun.cmd eol=crlf\nlogo.png -text\n", encoding="utf-8"
    )
    (repo / "docs").mkdir()
    (repo / "docs/.gitattributes").write_text("*.md !eol\n", encoding="utf-8")
    paths = ("README.md", "run.cmd", "logo.png", "docs/guide.md", 'docs/über "quoted".txt')
    assert checkout_line_endings(repo, paths) == {
        "README.md": ("auto", "lf"),
        "run.cmd": ("auto", "crlf"),
        "logo.png": ("unset", "lf"),
        "docs/guide.md": ("auto", "unspecified"),
        'docs/über "quoted".txt': ("auto", "lf"),
    }
    assert checkout_line_endings(repo, ()) == {}


def test_text_paths_follow_native_git_content_and_attribute_classification(
    tmp_path: Path,
) -> None:
    """Git's own classification decides text: a NUL byte or an unset text attribute is not."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / ".gitattributes").write_text("* text=auto eol=lf\nrelabeled.md -text\n")
    sources = {
        "plain.md": b"# Plain\n",
        "nul.md": b"# Nul\0\n",
        "relabeled.md": b"# Relabeled\n",
        "crlf.md": b"# Worktree CRLF\r\n",
        "empty.md": b"",
        "[literal]*.md": b"# Literal\n",
    }
    for relative, content in sources.items():
        (repo / relative).write_bytes(content)
    git(repo, "add", "--", ".gitattributes", "plain.md", "nul.md", "relabeled.md", "crlf.md")
    (repo / "untracked-nul.md").write_bytes(b"# Untracked\0\n")
    paths = (*sources, "untracked-nul.md")

    assert text_paths(repo, paths) == {"plain.md", "crlf.md", "empty.md", "[literal]*.md"}
    assert text_paths(repo, ()) == frozenset()
    assert text_paths(repo, ("absent.md",)) is None


def test_attribute_observations_conclude_nothing_when_git_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable observation receives no name and leaves every checkout unobserved."""
    refused = subprocess.CompletedProcess(("git",), 128, b"", b"fatal: not a git repository")
    truncated = subprocess.CompletedProcess(("git",), 0, b"assets/fonts/OFL.txt\0", b"")
    for completed in (refused, truncated):
        monkeypatch.setattr(git_attributes, "run_git", lambda *_args, _c=completed, **_o: _c)
        assert received_paths(tmp_path, ("assets/fonts/OFL.txt",)) == frozenset()
        assert checkout_line_endings(tmp_path, ("assets/fonts/OFL.txt",)) is None
        assert text_paths(tmp_path, ("assets/fonts/OFL.txt",)) is None
