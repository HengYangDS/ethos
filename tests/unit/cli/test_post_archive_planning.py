"""Plan from fresh post-archive state without reviving historical intent."""

from __future__ import annotations

from functools import partial
from pathlib import Path

import pytest

import ethos.adapters.admission.current.resolution as resolution_adapter
import ethos.domain.plan as planning_domain
import ethos.surface.cli.root.planning as planning_cli
from ethos.adapters.admission.current.resolution import current_scope
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.contracts.branch.roles import ROLE_WORK_LANE
from tests.support.semantic import commitment_fixture
from tests.unit.admission.current.support import authority


@pytest.fixture
def planning_case(monkeypatch, tmp_path):
    """Reuse the same observation and result boundary for both public consumers."""
    status = {
        "head": "a" * 40,
        "branch": "dev",
        "role": "accepted_root",
        "dirty": False,
        "changed_paths": [],
        "candidate": {},
        "foreign_work_lanes": [],
    }
    emitted = []
    for name, operation in {
        "repository_identity": lambda _repo: "repository:test",
        "workspace_status_observation": lambda _repo: (status, None),
        "closeout_command_from_status": lambda *_args: "",
    }.items():
        monkeypatch.setattr(planning_domain, name, operation)
    monkeypatch.setattr(planning_cli, "emit", lambda result, **_kwargs: emitted.append(result))

    def invoke_cli(**arguments):
        planning_cli.plan(root=tmp_path, json_output=True, **arguments)
        return emitted.pop()

    return partial(planning_domain.plan_repository, tmp_path), invoke_cli


def test_clean_changed_plan_closes_before_historical_intent_resolution(
    monkeypatch, planning_case, capsys
) -> None:
    def unexpected_resolution(*_args, **_kwargs):
        message = "an empty fresh changed set must not select historical intent"
        raise AssertionError(message)

    monkeypatch.setattr(planning_domain, "resolve_current_resolution", unexpected_resolution)
    for operation in planning_case:
        before = Path.cwd()
        result = operation(changed=True)
        assert Path.cwd() == before
        assert not capsys.readouterr().out
        assert result.verdict == "pass"
        assert result.state == "no_changes"
        assert result.summary == {
            "changed": False,
            "plan_node_count": 0,
            "matched_rule_count": 0,
            "required_gate_count": 0,
            "required_skill_count": 0,
        }
        assert result.required_gaps == ()
        assert result.next_action == ""
        assert result.to_dict()["data"] == {
            "changed_paths": [],
            "selected_carrier": "",
            "path_attributions": [],
            "matched_rules": [],
            "required_gates": [],
        }


@pytest.mark.parametrize(("changed", "change"), [(False, None), (True, "explicit-change")])
def test_empty_scope_does_not_bypass_ordinary_or_explicit_planning(
    monkeypatch, planning_case, *, changed: bool, change: str | None
) -> None:
    def expected_resolution(*_args, **_kwargs):
        message = "current intent resolution reached"
        raise RuntimeError(message)

    monkeypatch.setattr(planning_domain, "resolve_current_resolution", expected_resolution)
    for operation in planning_case:
        with pytest.raises(RuntimeError, match="current intent resolution reached"):
            operation(changed=changed, change=change)


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


@pytest.mark.parametrize(
    "extra",
    [
        "",
        "openspec_requested_change_missing:fixture-change",
        "openspec_list_unreadable",
        "openspec_validation_failed:spec:contracts",
    ],
)
def test_current_resolution_recovers_exact_archive_effect(
    monkeypatch, tmp_path: Path, extra
) -> None:
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
            "required_gaps": ["openspec_active_change_missing"] + ([extra] if extra else []),
            "commitment": {},
            "lifecycle": {"scope_binding": {}},
        },
    )
    resolution = resolve_current_resolution(
        tmp_path,
        status={"role": ROLE_WORK_LANE, "head": head},
        authority=authority(),
        change="fixture-change",
    )

    if extra and not extra.startswith("openspec_requested_change_missing:"):
        assert (resolution.verdict, resolution.commitment) == ("block", None)
        return
    assert resolution.commitment == commitment
    assert resolution.scope.paths == observed_paths
    assert resolution.scope.archive_authority == archive_authority
    assert resolution.openspec["verdict"] == "pass"
    assert resolution.openspec["required_gaps"] == []
