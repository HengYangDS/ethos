from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.mutation.resolution.records.roots import current_record_root
from ethos.adapters.mutation.resolution.records.roots import historical_record_roots
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_record_roots_separate_current_v2_from_immutable_history(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    current = current_record_root(repo)
    history = historical_record_roots(repo)

    assert current == tmp_path / "repo-records/recovery/lane-resolution-v2"
    assert history == (
        tmp_path / "repo-records/recovery/lane-resolution",
        repo / "build/artifacts/lane-resolution",
    )
    assert current not in history


def test_current_record_root_does_not_fallback_to_populated_history(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    history = historical_record_roots(repo)
    for record_root in history:
        record_root.mkdir(parents=True)

    current = current_record_root(repo)

    assert current == tmp_path / "repo-records/recovery/lane-resolution-v2"
    assert not current.exists()
    assert all(record_root.is_dir() for record_root in history)
