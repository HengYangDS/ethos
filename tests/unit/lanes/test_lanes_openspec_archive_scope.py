from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.lifecycle.scope as openspec_scope
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def _archive_scope_repo(
    tmp_path: Path,
    *,
    name: str,
    scope_payload: str | None,
) -> tuple[Path, Path]:
    """Create an adopter fixture with one archived OpenSpec change."""
    repo = init_repo(tmp_path / "repo")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text(
        '[openspec]\nmaterial_paths = ["guidelines.md", "openspec/**"]\n',
        encoding="utf-8",
    )
    archive = repo / "openspec" / "changes" / "archive" / name
    archive.mkdir(parents=True)
    if scope_payload is not None:
        (archive / "scope.toml").write_text(scope_payload, encoding="utf-8")
    metadata = archive / ".openspec.yaml"
    metadata.write_text("schema: spec-driven\ncreated: 2026-07-15\n", encoding="utf-8")
    return repo, metadata


def test_scope_reader_admits_current_archive_scope_only_for_current_diff(
    tmp_path: Path,
) -> None:
    """A valid archive scope covers only the archive reconciliation that carries it."""
    name = "2026-07-15-matching"
    repo, metadata = _archive_scope_repo(
        tmp_path,
        name=name,
        scope_payload='schema_version = 1\npaths = ["guidelines.md", "openspec/**"]\n',
    )
    current = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=("guidelines.md", metadata.relative_to(repo).as_posix()),
        active_change_names=(),
    )

    assert current["state"] == "covered"
    assert current["covered_paths"] == [
        {"path": "guidelines.md", "changes": [name]},
        {"path": metadata.relative_to(repo).as_posix(), "changes": [name]},
    ]

    historical = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=("guidelines.md",),
        active_change_names=(),
    )

    assert historical["state"] == "uncovered"
    assert historical["required_gaps"] == ["openspec_material_path_uncovered:guidelines.md"]


@pytest.mark.parametrize(
    ("name", "scope_payload", "diagnostic"),
    [
        (
            "2026-07-15-missing",
            None,
            "openspec_archive_scope_missing:2026-07-15-missing",
        ),
        (
            "2026-07-15-broken",
            "paths = [\n",
            "openspec_archive_scope_invalid:2026-07-15-broken",
        ),
    ],
)
def test_scope_reader_rejects_unusable_current_archive_scope(
    tmp_path: Path,
    name: str,
    scope_payload: str | None,
    diagnostic: str,
) -> None:
    """A missing or malformed archive companion cannot cover final reconciliation."""
    repo, metadata = _archive_scope_repo(
        tmp_path,
        name=name,
        scope_payload=scope_payload,
    )
    metadata_path = metadata.relative_to(repo).as_posix()

    report = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=("guidelines.md", metadata_path),
        active_change_names=(),
    )

    assert report["state"] == "uncovered"
    assert report["required_gaps"] == [
        "openspec_material_path_uncovered:guidelines.md",
        f"openspec_material_path_uncovered:{metadata_path}",
    ]
    assert report["advisory_gaps"] == [diagnostic]
