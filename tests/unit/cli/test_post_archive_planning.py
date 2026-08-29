from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.openspec.start_effect import current_generation_scope
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def test_post_archive_planning_uses_fresh_git_paths_not_an_archived_carrier(
    tmp_path: Path,
) -> None:
    paths = (
        "openspec/changes/archive/2026-08-28-fixture-change/proposal.md",
        "openspec/changes/archive/2026-08-28-fixture-change/tasks.md",
        "openspec/specs/contracts/spec.md",
    )
    lease = {
        "lane_ref": "work/fixture-change",
        "holder_ref": "agent:test",
        "generation": 1,
        "expires_at": "2026-08-29T00:00:00Z",
    }

    scope = current_generation_scope(
        tmp_path,
        head="a" * 40,
        repository_id="repository:test",
        commitment=commitment_fixture(id="change:fixture-change"),
        lease=lease,
        fallback_paths=paths,
    )

    assert scope.paths == paths
    assert scope.selected_carrier == ""
    assert scope.start_authority == {}
    assert scope.archive_authority == {}
    assert [item.path for item in scope.attributions] == list(paths)
    assert {item.source for item in scope.attributions} == {"git_changed_path"}
    assert {item.state for item in scope.attributions} == {"observed"}


def test_post_archive_planning_ignores_lease_payload_beyond_coordination(
    tmp_path: Path,
) -> None:
    commitment = commitment_fixture(id="change:fixture-change")
    paths = ("openspec/changes/archive/2026-08-28-fixture-change/design.md",)
    first = current_generation_scope(
        tmp_path,
        head="a" * 40,
        repository_id="repository:test",
        commitment=commitment,
        lease={
            "lane_ref": "work/fixture-change",
            "holder_ref": "agent:first",
            "generation": 1,
            "expires_at": "2026-08-29T00:00:00Z",
        },
        fallback_paths=paths,
    )
    second = current_generation_scope(
        tmp_path,
        head="b" * 40,
        repository_id="repository:test",
        commitment=commitment,
        lease={
            "lane_ref": "work/fixture-change",
            "holder_ref": "agent:second",
            "generation": 9,
            "expires_at": "2026-09-01T00:00:00Z",
        },
        fallback_paths=paths,
    )

    assert first == second
