"""Tests for the sole OpenSpec Change identifier and carrier grammar."""

from datetime import date

import pytest

from ethos.repository.openspec.identifiers import active_change_commitment
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import active_change_scope
from ethos.repository.openspec.identifiers import archived_change_commitment
from ethos.repository.openspec.identifiers import archived_change_commitment_matches
from ethos.repository.openspec.identifiers import archived_change_root
from ethos.repository.openspec.identifiers import change_root_from_commitment
from ethos.repository.openspec.identifiers import parse_change_commitment


def test_active_carrier_projects_root_commitment_and_scope() -> None:
    assert active_change_root("lineage-dag") == "openspec/changes/lineage-dag"
    assert active_change_commitment("lineage-dag") == (
        "openspec/changes/lineage-dag/commitment.toml"
    )
    assert active_change_scope("lineage-dag") == "openspec/changes/lineage-dag/**"


def test_archived_carrier_round_trips_exact_date_and_change() -> None:
    root = archived_change_root("lineage-dag", date(2026, 8, 22))
    carrier = archived_change_commitment("lineage-dag", date(2026, 8, 22))

    assert root == "openspec/changes/archive/2026-08-22-lineage-dag"
    assert parse_change_commitment(carrier) == ("lineage-dag", date(2026, 8, 22))
    assert archived_change_commitment_matches(carrier, "lineage-dag")
    assert not archived_change_commitment_matches(carrier, "other-change")
    assert change_root_from_commitment(carrier) == root
    assert parse_change_commitment(active_change_commitment("lineage-dag")) == (
        "lineage-dag",
        None,
    )


@pytest.mark.parametrize(
    "path",
    [
        "openspec/changes/archive/2026-02-30-lineage-dag/commitment.toml",
        "openspec/changes/Lineage/commitment.toml",
        "openspec/changes/lineage-dag/tasks.md",
        "openspec/changes/nested/lineage-dag/commitment.toml",
        "other/changes/lineage-dag/commitment.toml",
    ],
)
def test_parse_commitment_rejects_paths_outside_the_carrier_grammar(path: str) -> None:
    assert parse_change_commitment(path) is None


def test_constructor_rejects_invalid_change_identity() -> None:
    with pytest.raises(ValueError, match="openspec_change_carrier_invalid"):
        active_change_commitment("Lineage")
