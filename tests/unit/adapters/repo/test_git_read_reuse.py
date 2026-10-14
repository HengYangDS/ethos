"""Reuse fixed Git answers without reusing failures, overrides or a replaced checkout."""

from __future__ import annotations

import shutil
from collections import OrderedDict
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.process as process_adapter
import ethos.adapters.repo.git_read_reuse as read_reuse
from ethos.adapters.repo.git import run_git
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

_NAME = "a" * 40


@pytest.fixture
def launches(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Record every Git process the adapter starts, beginning with an empty reuse store."""
    monkeypatch.setattr(read_reuse, "_ANSWERS", OrderedDict())
    started: list[tuple[str, ...]] = []
    original = process_adapter.run_command

    def counted(root, command, **options):
        started.append(tuple(command[1:]))
        return original(root, command, **options)

    monkeypatch.setattr(process_adapter, "run_command", counted)
    return started


def test_named_object_reads_start_one_process_per_checkout(
    tmp_path: Path, launches: list[tuple[str, ...]]
) -> None:
    """A repeated read of named objects and of the common directory is answered once."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    reads = (
        ("show", f"{head}:README.md"),
        ("rev-parse", f"{head}^{{tree}}"),
        ("rev-parse", "--git-common-dir"),
        ("ls-tree", "-r", "-z", head),
    )
    first = [run_git(repo, *read) for read in reads]
    second = [run_git(repo, *read) for read in reads]
    assert [answer.stdout for answer in second] == [answer.stdout for answer in first]
    assert first[0].stdout == "# sample\n"
    assert launches == list(reads)
    second[0].stdout = "changed by a caller"
    assert run_git(repo, *reads[0]).stdout == "# sample\n"


def test_moving_failed_and_overridden_reads_start_every_time(
    tmp_path: Path, launches: list[tuple[str, ...]]
) -> None:
    """Only a successful fixed read without overrides is reused; ref reads stay fresh."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    for _ in range(2):
        assert run_git(repo, "rev-parse", "HEAD").stdout.strip() == head
        assert run_git(repo, "show", f"{_NAME}:README.md", check=False).returncode != 0
        run_git(repo, "show", f"{head}:README.md", env={"LC_ALL": "C"})
        run_git(repo, "show", f"{head}:README.md", stdin="")
    assert len(launches) == 8
    (repo / "next.txt").write_text("next\n", encoding="utf-8")
    moved = commit_fixture(repo, "next")
    assert run_git(repo, "rev-parse", "HEAD").stdout.strip() == moved != head


def test_recreated_checkout_is_not_answered_from_the_former_repository(
    tmp_path: Path, launches: list[tuple[str, ...]]
) -> None:
    """A repository rebuilt at the same path observes its own objects again."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "only.txt").write_text("former\n", encoding="utf-8")
    former = commit_fixture(repo, "former only")
    assert run_git(repo, "show", f"{former}:only.txt").stdout == "former\n"
    shutil.rmtree(repo)
    init_git_repo(repo)
    assert run_git(repo, "show", f"{former}:only.txt", check=False).returncode != 0
    assert launches.count(("show", f"{former}:only.txt")) == 2


def test_reads_outside_a_checkout_and_beyond_capacity_start_again(
    tmp_path: Path, launches: list[tuple[str, ...]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A directory without its own Git entry is never keyed, and eviction keeps the bound."""
    repo = init_git_repo(tmp_path / "repo")
    nested = repo / "nested"
    nested.mkdir()
    for _ in range(2):
        run_git(nested, "version")
    monkeypatch.setattr(read_reuse, "_CAPACITY", 1)
    head = git(repo, "rev-parse", "HEAD")
    for read in (("version",), ("rev-parse", f"{head}^{{tree}}"), ("version",)):
        run_git(repo, *read)
    assert launches == [("version",)] * 2 + [
        ("version",),
        ("rev-parse", f"{head}^{{tree}}"),
        ("version",),
    ]


@pytest.mark.parametrize(
    ("args", "fixed"),
    [
        (("version",), True),
        (("rev-parse", "--git-common-dir"), True),
        (("show", f"{_NAME}:path/file"), True),
        (("rev-parse", f"{_NAME}^{{tree}}"), True),
        (("cat-file", "commit", _NAME), True),
        (("merge-base", "--is-ancestor", _NAME, _NAME), True),
        (("ls-tree", _NAME), True),
        (("ls-tree", "-r", "--name-only", "-z", _NAME), True),
        (("show", "HEAD:path/file"), False),
        (("show", _NAME), False),
        (("rev-parse", "HEAD"), False),
        (("rev-parse", "HEAD^{tree}"), False),
        (("read-tree", _NAME), False),
        (("cat-file", "--batch"), False),
        (("cat-file", "-p", _NAME), False),
        (("merge-base", _NAME, _NAME), False),
        (("merge-base", "--is-ancestor", "HEAD", _NAME), False),
        (("ls-tree", _NAME, "--", "path"), False),
    ],
)
def test_only_reads_fixed_by_their_stated_names_qualify(
    args: tuple[str, ...], *, fixed: bool
) -> None:
    """Mutable refs, writes, batch input and pathspec-limited listings never qualify."""
    assert read_reuse.fixed_answer(args) is fixed
