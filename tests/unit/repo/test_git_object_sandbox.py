"""Keep candidate Git objects and temporary execution out of the source repository."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

import ethos.adapters.repo.git_object_sandbox as sandbox
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object_sandbox import isolated_git_objects
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_isolated_objects_can_read_source_but_cannot_publish_into_it(
    tmp_path: Path, object_format: str
) -> None:
    """An alternate is a read-only source, not a second writer to the adopter."""
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    head = git(repo, "rev-parse", "HEAD")
    refs = git(repo, "show-ref")
    content = f"temporary candidate {uuid4()}"

    with isolated_git_objects(repo) as isolated:
        assert isolated("cat-file", "-t", head).stdout.strip() == "commit"
        created = isolated("hash-object", "-w", "--stdin", stdin=content).stdout.strip()
        assert isolated("cat-file", "-p", created).stdout == content
        assert run_git(repo, "cat-file", "-e", created, check=False).returncode != 0

    assert run_git(repo, "cat-file", "-e", created, check=False).returncode != 0
    assert git(repo, "show-ref") == refs
    assert git(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize("source", ["command-failed", "relative-objects", "missing-objects"])
def test_isolated_objects_rejects_untrusted_source_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source: str
) -> None:
    """A failed or unsafe source observation cannot open a writable sandbox."""
    repo = init_git_repo(tmp_path / "repo")
    head, refs = git(repo, "rev-parse", "HEAD"), git(repo, "show-ref")
    code, output = {
        "command-failed": (1, ""),
        "relative-objects": (0, "relative\nsha1\n"),
        "missing-objects": (0, f"{tmp_path / 'missing'}\nsha1\n"),
    }[source]
    observed = subprocess.CompletedProcess(("git",), code, stdout=output, stderr="")
    monkeypatch.setattr(sandbox, "run_git", lambda *_args, **_kwargs: observed)

    with (
        pytest.raises(ValueError, match="git_object_source_unavailable"),
        isolated_git_objects(repo),
    ):
        pytest.fail("untrusted source admitted")

    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "show-ref") == refs
