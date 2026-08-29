"""Tests for the official OpenSpec Change identifier and root grammar."""

from datetime import date

import pytest

from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import active_change_scope
from ethos.repository.openspec.identifiers import archived_change_root
from ethos.repository.openspec.identifiers import archived_change_root_matches
from ethos.repository.openspec.identifiers import parse_archived_change_root


def test_active_change_projects_only_the_official_root() -> None:
    assert active_change_root("lineage-dag") == "openspec/changes/lineage-dag"
    assert active_change_scope("lineage-dag") == "openspec/changes/lineage-dag/**"


def test_archived_root_round_trips_exact_date_and_change() -> None:
    root = archived_change_root("lineage-dag", date(2026, 8, 22))

    assert root == "openspec/changes/archive/2026-08-22-lineage-dag"
    assert parse_archived_change_root(root) == ("lineage-dag", date(2026, 8, 22))
    assert archived_change_root_matches(root, "lineage-dag")
    assert not archived_change_root_matches(root, "other-change")


@pytest.mark.parametrize(
    "path",
    [
        "openspec/changes/archive/2026-02-30-lineage-dag",
        "openspec/changes/Lineage",
        "openspec/changes/lineage-dag/tasks.md",
        "openspec/changes/nested/lineage-dag",
        "other/changes/lineage-dag",
    ],
)
def test_parse_archive_rejects_paths_outside_the_root_grammar(path: str) -> None:
    assert parse_archived_change_root(path) is None


def test_constructor_rejects_invalid_change_identity() -> None:
    with pytest.raises(ValueError, match="openspec_change_root_invalid"):
        active_change_root("Lineage")
