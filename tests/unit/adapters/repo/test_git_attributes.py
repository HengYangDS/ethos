"""Native Git attribute observations of tracked paths."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.repo.git_attributes as git_attributes
from ethos.adapters.repo.git_attributes import received_paths
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


def test_received_paths_are_empty_when_git_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable attribute observation receives nothing, so every name is still judged."""
    refused = subprocess.CompletedProcess(("git",), 128, b"", b"fatal: not a git repository")
    monkeypatch.setattr(git_attributes, "run_git", lambda *_args, **_options: refused)
    assert received_paths(tmp_path, ("assets/fonts/OFL.txt",)) == frozenset()
    truncated = subprocess.CompletedProcess(("git",), 0, b"assets/fonts/OFL.txt\0", b"")
    monkeypatch.setattr(git_attributes, "run_git", lambda *_args, **_options: truncated)
    assert received_paths(tmp_path, ("assets/fonts/OFL.txt",)) == frozenset()
