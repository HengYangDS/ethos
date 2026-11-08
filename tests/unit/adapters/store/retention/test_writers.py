"""A batch defers only while a process runs one of the repository's other ETHOS interpreters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.repo.runtime.host_store import record_consumer
from ethos.adapters.store.retention.writers import running_writers
from ethos.adapters.store.retention.writers import writer_roots
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _entry(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    return path


def test_only_a_command_that_starts_from_a_writer_root_counts(tmp_path: Path) -> None:
    """The command's own executable, or a launcher's script, decides; a mention does not."""
    generation = tmp_path / "common/ethos/runtime/aaa"
    environment = tmp_path / "lane/.venv"
    installation = tmp_path / "Application Support/ethos/installations/bbb"
    python = _entry(generation / "python/bin/python3")
    ethos = _entry(environment / "bin/ethos")
    installed = _entry(installation / "python/bin/python3")
    shell = _entry(tmp_path / "bin/zsh")
    reader = _entry(tmp_path / "bin/cat")
    roots = (generation, environment, installation)
    listing = "\n".join(
        (
            f"{python} -B -m ethos.cli status",
            f"{shell} {ethos} lane status",
            f"{installed} -m ethos.cli hook pre-commit",
            f"{reader} {ethos}",
            f"{shell} -c echo {environment}",
            "ruff server",
        )
    )

    assert running_writers(listing, roots) == (generation, environment, installation)
    assert running_writers(f"{reader} {ethos}\nruff server", roots) == ()


def test_the_writer_roots_are_this_repositorys_other_interpreters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Other generations, installations it or unknown consumers use, and lane environments count."""
    repo = init_git_repo(tmp_path / "repo")
    common = (repo / ".git").resolve()
    selected = common / "ethos/runtime" / ("a" * 64)
    other = common / "ethos/runtime" / ("b" * 64)
    for generation in (selected, other):
        generation.mkdir(parents=True)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    installations = tmp_path / "xdg/ethos/installations"
    used, foreign, unknown = (installations / name for name in ("c" * 64, "d" * 64, "e" * 64))
    for installation in (used, foreign, unknown):
        installation.mkdir(parents=True)
    record_consumer(used, common)
    record_consumer(foreign, tmp_path / "elsewhere/.git")
    _entry(repo / ".venv/bin/ethos")

    roots = writer_roots(repo, selected=selected)

    assert roots == (other, used.resolve(), unknown.resolve(), (repo / ".venv").resolve())
    assert writer_roots(repo, selected=used) == (
        selected,
        other,
        unknown.resolve(),
        (repo / ".venv").resolve(),
    )
