from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.admission.current.resolution as resolution_adapter
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.admission.current.resolution import current_scope
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


def test_post_archive_planning_uses_fresh_git_paths_not_an_archived_carrier() -> None:
    paths = (
        "openspec/changes/archive/2026-08-28-fixture-change/proposal.md",
        "openspec/changes/archive/2026-08-28-fixture-change/tasks.md",
        "openspec/specs/contracts/spec.md",
    )
    scope = current_scope(
        commitment=commitment_fixture(id="change:fixture-change"),
        fallback_paths=paths,
    )

    assert scope.paths == paths
    assert scope.selected_carrier == ""
    assert scope.archive_authority == {}
    assert [item.path for item in scope.attributions] == list(paths)
    assert {item.source for item in scope.attributions} == {"git_changed_path"}
    assert {item.state for item in scope.attributions} == {"observed"}


def test_post_archive_planning_ignores_lease_payload_beyond_coordination() -> None:
    commitment = commitment_fixture(id="change:fixture-change")
    paths = ("openspec/changes/archive/2026-08-28-fixture-change/design.md",)
    first = current_scope(
        commitment=commitment,
        fallback_paths=paths,
    )
    second = current_scope(
        commitment=commitment,
        fallback_paths=paths,
    )

    assert first == second


def test_current_resolution_recovers_exact_archive_effect(monkeypatch, tmp_path: Path) -> None:
    head = "a" * 40
    archive_paths = (
        "openspec/changes/archive/2026-08-29-fixture-change/tasks.md",
        "src/fixture.py",
    )
    observed_paths = (*archive_paths, "src/post-archive-repair.py")
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

    def load(*_args, **_kwargs):
        message = "the exact archive Attestation owns post-archive intent"
        raise AssertionError(message)

    def archived(_root: Path, *, head: str, change: str | None):
        assert head == "a" * 40
        assert change == "fixture-change"
        return commitment, archive_authority

    monkeypatch.setattr(resolution_adapter, "load_profile_commitment", load)
    monkeypatch.setattr(
        resolution_adapter,
        "change_scope_paths_from_status",
        lambda *_args: observed_paths,
    )
    monkeypatch.setattr(
        resolution_adapter,
        "attested_archive_transition",
        archived,
    )
    monkeypatch.setattr(
        resolution_adapter,
        "openspec_governance_report",
        lambda *_args, **_kwargs: {
            "verdict": "block",
            "required_gaps": ["openspec_active_change_missing"],
            "commitment": {},
            "lifecycle": {"scope_binding": {}},
        },
    )
    authority = CurrentAuthority(
        verdict="pass",
        reason="matched",
        branch="work/fixture-change",
        actor="agent:test",
        lease={
            "lane_ref": "work/fixture-change",
            "holder_ref": "agent:test",
            "generation": 1,
            "expires_at": "2026-08-30T00:00:00Z",
        },
        current_head=head,
        current_tree="b" * 40,
    )

    resolution = resolve_current_resolution(
        tmp_path,
        status={"role": ROLE_WORK_LANE, "head": head},
        authority=authority,
        change="fixture-change",
    )

    assert resolution.commitment == commitment
    assert resolution.scope.paths == observed_paths
    assert resolution.scope.archive_authority == archive_authority
    assert resolution.openspec["verdict"] == "pass"
    assert resolution.openspec["required_gaps"] == []
