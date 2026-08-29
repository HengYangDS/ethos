from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.openspec.start_effect as start_effect
from ethos.adapters.openspec.start_effect import current_generation_scope
from ethos.contracts.branch.roles import ROLE_WORK_LANE
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


def test_current_generation_binding_recovers_exact_archive_effect(
    monkeypatch, tmp_path: Path
) -> None:
    head = "a" * 40
    archive_paths = (
        "openspec/changes/archive/2026-08-29-fixture-change/tasks.md",
        "src/fixture.py",
    )
    commitment = commitment_fixture(id="change:fixture-change")
    archive_authority = {
        "predicate": "effect:git-ref-update",
        "source": "archive_commit",
        "claim": {"operation": "openspec.archive"},
        "attestation_id": "b" * 64,
        "effect_digest": "c" * 64,
        "plan_digest": "d" * 64,
        "authorized_paths": list(archive_paths),
    }
    calls: list[str | None] = []

    def load(_root: Path, *, change_id=None, tree_ref=None):
        calls.append(tree_ref)
        if tree_ref is None:
            message = "openspec_active_change_missing"
            raise ValueError(message)
        assert change_id is None
        assert tree_ref == head
        return commitment

    def archived(_root: Path, *, head: str, change: str | None):
        assert head == "a" * 40
        assert change is None
        return commitment, archive_authority

    monkeypatch.setattr(start_effect, "load_profile_commitment", load)
    monkeypatch.setattr(
        start_effect,
        "change_scope_paths_from_status",
        lambda *_args: ("src/unrelated-work-lane-history.py",),
    )
    monkeypatch.setattr(
        start_effect,
        "attested_archive_transition",
        archived,
        raising=False,
    )
    authority = SimpleNamespace(
        verdict="pass",
        reason="matched",
        lease={
            "lane_ref": "work/fixture-change",
            "holder_ref": "agent:test",
            "generation": 1,
            "expires_at": "2026-08-30T00:00:00Z",
        },
    )

    binding = start_effect.current_generation_binding(
        tmp_path,
        status={"role": ROLE_WORK_LANE, "head": head},
        repository_id="repository:test",
        authority=authority,
    )

    assert calls == [None]
    assert binding.commitment == commitment
    assert binding.scope.paths == archive_paths
    assert binding.scope.archive_authority == archive_authority
