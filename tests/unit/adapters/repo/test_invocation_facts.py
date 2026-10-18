"""Within one application invocation, Git reads one immutable object once."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.process as process_adapter
from ethos.adapters.repo import invocation_facts
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.invocation_facts import invocation_scope
from ethos.adapters.repo.runtime import authority
from ethos.domain.execution import application_result
from ethos.result import EthosResult
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


@pytest.fixture
def launched(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Record the Git arguments of every process actually started."""
    started: list[tuple[str, ...]] = []
    original = process_adapter.run_command

    def recording(root: Path, command: tuple[str, ...], **kwargs: Any) -> Any:
        started.append(tuple(command[1:]))
        return original(root, command, **kwargs)

    monkeypatch.setattr(process_adapter, "run_command", recording)
    return started


def _immutable_reads(head: str) -> tuple[tuple[str, ...], ...]:
    return (
        ("rev-parse", "--verify", "--quiet", f"{head}^{{tree}}"),
        ("show", f"{head}:README.md"),
        ("cat-file", "-p", head),
        ("ls-tree", "-r", "-z", head),
        ("merge-base", "--is-ancestor", head, head),
    )


def test_an_invocation_reads_each_immutable_object_once(
    tmp_path: Path, launched: list[tuple[str, ...]]
) -> None:
    """Repeated reads named only by full object IDs reuse the first successful result."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    with invocation_scope():
        first = [run_git(repo, *argv).stdout for argv in _immutable_reads(head)]
        again = [run_git(repo, *argv).stdout for argv in _immutable_reads(head)]
    after = run_git(repo, *_immutable_reads(head)[0]).stdout

    assert again == first
    assert after == first[0]
    assert launched == [*_immutable_reads(head), _immutable_reads(head)[0]]


@pytest.mark.parametrize(
    "argv",
    [
        lambda _head: ("rev-parse", "HEAD"),
        lambda head: ("rev-parse", head[:12]),
        lambda head: ("show", head),
        lambda _head: ("show",),
        lambda head: ("cat-file", "--textconv", f"{head}:README.md"),
        lambda _head: ("rev-list", "--all"),
        lambda head: ("merge-base", "--fork-point", head),
        lambda head: ("-c", "core.quotePath=false", "rev-parse", head),
        lambda _head: ("status", "--porcelain"),
    ],
)
def test_mutable_or_interpreted_reads_are_observed_every_time(
    tmp_path: Path, launched: list[tuple[str, ...]], argv: Callable[[str], tuple[str, ...]]
) -> None:
    """Refs, abbreviations, worktree state and configuration-dependent output stay fresh."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    with invocation_scope():
        run_git(repo, *argv(head), check=False)
        run_git(repo, *argv(head), check=False)

    assert launched == [argv(head), argv(head)]


def test_overridden_input_or_environment_is_observed_every_time(
    tmp_path: Path, launched: list[tuple[str, ...]]
) -> None:
    """A caller's stdin, environment or spooled output is never answered from reuse."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    tree = ("rev-parse", f"{head}^{{tree}}")

    with invocation_scope():
        for _ in range(2):
            run_git(repo, *tree, env={"GIT_NOTES_REF": "refs/notes/other"})
            run_git(repo, *tree, stdin="")
            run_git(repo, *tree, spool_stdout=True, text=False)

    assert launched == [tree] * 6


def test_a_failed_read_is_observed_again_until_it_succeeds(
    tmp_path: Path, launched: list[tuple[str, ...]]
) -> None:
    """An object that is absent now may arrive later, so only success is reused."""
    repo = init_git_repo(tmp_path / "repo")
    (repo / "arrived.txt").write_text("arrived\n", encoding="utf-8")
    blob = git(repo, "hash-object", "arrived.txt")
    exists = ("cat-file", "-e", blob)

    with invocation_scope():
        missing = run_git(repo, *exists, check=False).returncode
        commit_fixture_file(repo, "arrived.txt", "arrived\n", "chore: add the object")
        present = run_git(repo, *exists, check=False).returncode
        reused = run_git(repo, *exists, check=False).returncode

    assert (missing != 0, present, reused) == (True, 0, 0)
    assert launched.count(exists) == 2


def test_a_reader_cannot_alter_a_reused_result(
    tmp_path: Path, launched: list[tuple[str, ...]]
) -> None:
    """Each reader receives its own result object."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    tree = ("rev-parse", f"{head}^{{tree}}")

    with invocation_scope():
        first = run_git(repo, *tree)
        expected = first.stdout
        first.stdout = "altered"
        second = run_git(repo, *tree)
        second.stdout = "altered again"
        third = run_git(repo, *tree)

    assert (second.stdout, third.stdout) == ("altered again", expected)
    assert len(launched) == 1


def test_nested_scopes_share_one_invocation_and_its_budget(
    tmp_path: Path, launched: list[tuple[str, ...]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An inner scope keeps the outer reuse, and output beyond the budget is not retained."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    tree = ("rev-parse", f"{head}^{{tree}}")
    show = ("show", f"{head}:README.md")
    monkeypatch.setattr(invocation_facts, "IMMUTABLE_READ_BYTES", len(f"{head}\n"))

    with invocation_scope():
        run_git(repo, *tree)
        with invocation_scope():
            run_git(repo, *tree)
            run_git(repo, *show)
        run_git(repo, *tree)
        run_git(repo, *show)

    assert launched == [tree, show, show]


def test_an_application_operation_reuses_its_immutable_reads(
    tmp_path: Path, launched: list[tuple[str, ...]]
) -> None:
    """Every operation behind the shared application boundary is one reuse invocation."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    tree = ("rev-parse", f"{head}^{{tree}}")

    @application_result("probe")
    def operation(root: Path) -> EthosResult:
        run_git(root, *tree)
        run_git(root, *tree)
        return EthosResult(command="probe", verdict="pass", state="observed")

    operation(repo)
    operation(repo)

    assert launched == [tree, tree]


def test_an_invocation_observes_the_running_build_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """The executing product's build is one fact per invocation and fresh across invocations."""
    observed: list[bool] = []

    def observe(_source: Path, *, include_overlay: bool = True) -> object:
        observed.append(include_overlay)
        return SimpleNamespace(source_commit=f"{len(observed):040x}")

    monkeypatch.setattr(authority, "source_build_identity", observe)
    with invocation_scope():
        first = authority.invoking_source_commit()
        second = authority.invoking_source_commit()
        authority.invoking_build_identity()
        authority.invoking_build_identity()
    later = authority.invoking_source_commit()

    assert first == second != later
    assert observed == [False, True, False]
