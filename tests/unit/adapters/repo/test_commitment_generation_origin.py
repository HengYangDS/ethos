"""Git-native Change carrier generation-origin contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

import tomli_w

from ethos.adapters.repo.commitment import commitment_generation_origin
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.semantic import commitment_v2

if TYPE_CHECKING:
    from pathlib import Path


def _write_change_carrier(root: Path, path: str, *, intent: str = "Track one origin.") -> None:
    carrier = root / path
    carrier.parent.mkdir(parents=True, exist_ok=True)
    carrier.write_text(
        tomli_w.dumps(
            commitment_v2(
                id="change:origin-change",
                intent=intent,
                subjects=("repository:test",),
                scope=("src/**",),
            ).model_dump(mode="python")
        ),
        encoding="utf-8",
    )


def test_origin_follows_repeated_exact_relocations(tmp_path: Path) -> None:
    repository, _candidate = start_adopted_candidate(tmp_path)
    first = "openspec/changes/origin-change/commitment.toml"
    second = "openspec/changes/renamed-origin/commitment.toml"
    third = "openspec/changes/final-origin/commitment.toml"
    origin = git(repository, "rev-parse", "HEAD")
    _write_change_carrier(repository, first)
    git(repository, "add", first)
    git(repository, "commit", "-m", "introduce origin carrier")
    (repository / second).parent.mkdir(parents=True, exist_ok=True)
    git(repository, "mv", first, second)
    git(repository, "commit", "-m", "relocate origin carrier")
    (repository / third).parent.mkdir(parents=True, exist_ok=True)
    git(repository, "mv", second, third)
    git(repository, "commit", "-m", "relocate origin carrier again")
    _write_change_carrier(repository, third, intent="Rebind the same Change carrier.")
    git(repository, "add", third)
    git(repository, "commit", "-m", "rebind relocated origin carrier")

    assert (
        commitment_generation_origin(
            repository,
            head=git(repository, "rev-parse", "HEAD"),
            carrier=third,
            change_id="origin-change",
        )
        == origin
    )


def test_origin_fails_closed_for_merge_ancestry(tmp_path: Path) -> None:
    repository, _candidate = start_adopted_candidate(tmp_path)
    carrier = "openspec/changes/origin-change/commitment.toml"
    _write_change_carrier(repository, carrier)
    git(repository, "add", carrier)
    git(repository, "commit", "-m", "introduce origin carrier")
    git(repository, "branch", "side")
    (repository / "README.md").write_text("# main\n", encoding="utf-8")
    git(repository, "add", "README.md")
    git(repository, "commit", "-m", "advance main")
    git(repository, "checkout", "side")
    (repository / "SIDE.md").write_text("side\n", encoding="utf-8")
    git(repository, "add", "SIDE.md")
    git(repository, "commit", "-m", "advance side")
    git(repository, "checkout", "dev")
    git(repository, "merge", "--no-ff", "side", "-m", "merge side")

    assert not commitment_generation_origin(
        repository,
        head=git(repository, "rev-parse", "HEAD"),
        carrier=carrier,
        change_id="origin-change",
    )


def test_origin_fails_closed_without_introduction_evidence(tmp_path: Path) -> None:
    repository, _candidate = start_adopted_candidate(tmp_path)

    assert not commitment_generation_origin(
        repository,
        head=git(repository, "rev-parse", "HEAD"),
        carrier="openspec/changes/origin-change/commitment.toml",
        change_id="origin-change",
    )
