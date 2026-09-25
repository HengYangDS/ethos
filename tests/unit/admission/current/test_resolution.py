"""Resolve current authority from exact paths, intent and artifact state."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

import ethos.adapters.admission.current.resolution as resolution_adapter
from ethos.adapters.admission.current.resolution import CurrentResolution
from ethos.adapters.admission.current.resolution import resolve_current_resolution
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import ROLE_CANDIDATE
from ethos.contracts.semantic import Commitment
from tests.support.semantic import commitment_fixture
from tests.unit.admission.current.support import HEAD
from tests.unit.admission.current.support import ROOT
from tests.unit.admission.current.support import authority
from tests.unit.admission.current.support import official_artifact
from tests.unit.admission.current.support import official_report
from tests.unit.admission.current.support import resolve_report

ACTIVE_SPEC = "openspec/changes/repair-change/specs/repository-governance/spec.md"


@pytest.mark.parametrize("changed", [False, True])
def test_prewrite_resolves_requested_paths_instead_of_workspace_diff(monkeypatch, changed):
    """Prewrite attributes the proposed effect, even before those files are dirty."""
    paths = ("src/example.py", "openspec/changes/example/tasks.md")
    commitment = commitment_fixture(id="change:example")

    def observe(_root, **kwargs):
        assert kwargs["changed_paths"] == paths
        return official_report(change="example", commitment=commitment.model_dump(mode="json")) | {
            "verdict": "pass"
        }

    monkeypatch.setattr(resolution_adapter, "openspec_governance_report", observe)
    monkeypatch.setattr(
        resolution_adapter,
        "change_scope_paths_from_status",
        lambda *_args: pytest.fail("exact prewrite must not expand to unrelated dirty paths"),
    )
    resolution = resolve_current_resolution(
        ROOT,
        status={"role": "work_lane", "head": HEAD, "changed_paths": ["unrelated.py"]},
        authority=authority(),
        changed=changed,
        prewrite_paths=paths,
    )
    assert resolution.verdict == "pass"
    assert resolution.scope.paths == paths
    assert resolution.scope_report()["covered_paths"] == [
        {"path": path, "changes": ["example"]} for path in paths
    ]


def test_current_resolution_preserves_the_first_authority_gap() -> None:
    resolution = resolve_current_resolution(
        ROOT,
        status={"role": "work_lane", "head": HEAD},
        authority=authority(verdict="block", reason="invocation_actor_missing:work/example"),
    )
    assert resolution.required_gaps == ("invocation_actor_missing:work/example",)
    assert resolution.next_action == "export ETHOS_ACTOR=agent:test"
    assert resolution.user_decision_required is False


def test_current_resolution_owns_acceptance_and_fresh_paths(monkeypatch) -> None:
    commitment = Commitment(
        schema_version=3,
        id="change:example",
        acceptance=("result projection is consistent",),
    )
    monkeypatch.setattr(resolution_adapter, "load_profile_commitment", lambda *_a, **_k: commitment)
    monkeypatch.setattr(
        resolution_adapter,
        "change_scope_paths_from_status",
        lambda *_a, **_k: ("src/example.py",),
    )
    resolution = resolve_current_resolution(
        ROOT, status={"role": "work_lane", "head": HEAD}, authority=authority()
    )
    assert isinstance(resolution, CurrentResolution)
    assert resolution.verdict == "pass"
    assert resolution.commitment == commitment
    assert resolution.scope.paths == ("src/example.py",)
    assert resolution.required_gaps == ()
    assert resolution.next_action == ""


@pytest.mark.parametrize("selection", ["explicit", "environment"])
@pytest.mark.parametrize(
    "gap", ["", "openspec_official_cli_missing", "openspec_acceptance_missing:example"]
)
def test_current_resolution_compiles_committed_source_intent_without_workspace_reread(
    monkeypatch, gap, selection
):
    monkeypatch.setenv("ETHOS_CHANGE", "example" if selection == "environment" else "other")
    commitment = commitment_fixture(id="change:example")
    calls: list[tuple[str | None, str | None]] = []
    observe = Mock(side_effect=AssertionError("committed intent must not read workspace"))
    monkeypatch.setattr(resolution_adapter, "openspec_governance_report", observe)

    def load(_root: Path, *, change_id: str | None, tree_ref: str | None = None):
        calls.append((change_id, tree_ref))
        if gap:
            raise ValueError(gap)
        return commitment

    monkeypatch.setattr(resolution_adapter, "load_profile_commitment", load)
    resolution = resolve_current_resolution(
        ROOT,
        status={"role": "work_lane", "head": HEAD, "changed_paths": []},
        authority=authority(),
        change="example" if selection == "explicit" else None,
        changed=False,
        intent_tree_ref=HEAD,
    )
    observe.assert_not_called()
    assert calls == [("example", HEAD)]
    if gap:
        assert resolution.verdict == "block"
        assert resolution.commitment is None
        assert resolution.required_gaps == (gap,)
        assert resolution.next_action == (
            "npm ci --ignore-scripts --no-audit --no-fund"
            if gap == "openspec_official_cli_missing"
            else "openspec status --change example --json"
        )
    else:
        assert resolution.verdict == "pass"
        assert resolution.commitment == commitment
        assert resolution.openspec == {
            "verdict": "pass",
            "state": "committed_source",
            "change": "example",
            "source_head": HEAD,
            "required_gaps": [],
        }


def test_current_resolution_preserves_unknown_official_intent_without_reinterpreting(monkeypatch):
    report = official_report(gaps=("carrier_unreadable",)) | {"verdict": "unknown"}
    load = Mock(side_effect=AssertionError("unknown official intent must stop resolution"))
    monkeypatch.setattr(resolution_adapter, "load_profile_commitment", load)
    resolution = resolve_report(monkeypatch, report, role=ROLE_ACCEPTED_ROOT)
    load.assert_not_called()
    assert resolution.verdict == "unknown"
    assert resolution.commitment is None
    assert resolution.required_gaps == ("carrier_unreadable",)


@pytest.mark.parametrize("role", [ROLE_CANDIDATE, ROLE_ACCEPTED_ROOT])
@pytest.mark.parametrize(
    ("official_verdict", "official_gaps"),
    [
        ("pass", []),
        ("block", ["openspec_active_change_missing"]),
    ],
)
def test_current_resolution_admits_entity_free_repository_proof(
    monkeypatch: pytest.MonkeyPatch,
    role: str,
    official_verdict: str,
    official_gaps: list[str],
) -> None:
    current = replace(
        authority(),
        branch="candidate/dev" if role == ROLE_CANDIDATE else "dev",
        required=False,
        reason="not_required",
        lease={},
    )
    observe = Mock(
        return_value={
            "verdict": official_verdict,
            "required_gaps": official_gaps,
            "commitment": {},
            "lifecycle": {"scope_binding": {}, "changes": []},
        }
    )
    load = Mock(side_effect=AssertionError("entity-free proof must not invent intent"))
    monkeypatch.setattr(resolution_adapter, "openspec_governance_report", observe)
    monkeypatch.setattr(resolution_adapter, "attested_archive_transition", Mock(return_value=None))
    monkeypatch.setattr(resolution_adapter, "load_profile_commitment", load)

    resolution = resolve_current_resolution(
        Path("/repository"),
        status={"role": role, "head": HEAD, "changed_paths": []},
        authority=current,
        changed=False,
    )

    load.assert_not_called()
    assert resolution.verdict == "pass"
    assert resolution.authority is current
    assert resolution.commitment is None
    assert resolution.scope.paths == ()
    assert resolution.openspec == {
        "verdict": "pass",
        "state": "not_applicable",
        "required_gaps": [],
    }


@pytest.mark.parametrize(
    ("path", "verdict"),
    [
        ("openspec/changes/example/.openspec.yaml", "pass"),
        ("openspec/changes/example/proposal.md", "pass"),
        ("openspec/changes/example/specs/capability/spec.md", "pass"),
        ("openspec/changes/example/design.md", "pass"),
        ("openspec/changes/example/tasks.md", "pass"),
        ("openspec/changes/example/README.md", "block"),
        ("openspec/changes/other/proposal.md", "block"),
        ("openspec/changes/archive/2026-08-30-example/tasks.md", "block"),
        ("src/product.py", "block"),
    ],
)
def test_current_resolution_projects_only_incomplete_official_change_artifacts_for_prewrite(
    monkeypatch,
    path: str,
    verdict: str,
) -> None:
    change = "example"
    artifacts = (
        official_artifact("proposal", "proposal.md", status="ready"),
        official_artifact("specs", "specs/**/*.md", status="blocked", requires=("proposal",)),
        official_artifact("design", "design.md", status="blocked", requires=("proposal",)),
        official_artifact("tasks", "tasks.md", status="blocked", requires=("specs", "design")),
    )
    resolution = resolve_report(
        monkeypatch,
        official_report(
            change=change,
            gaps=(f"openspec_status_incomplete:{change}",),
            artifacts=artifacts,
            change_path=f"openspec/changes/{change}",
            scope_binding={"verdict": "pass", "state": "no_material_paths"},
        ),
        paths=(path,),
    )
    assert resolution.verdict == verdict
    assert resolution.commitment is None
    assert resolution.scope.material_scope["state"] == "official_change_bootstrap"
    assert resolution.next_action == f"openspec instructions proposal --change {change} --json"


@pytest.mark.parametrize("target", ["metadata", "absent-root", "existing-root"])
def test_current_resolution_derives_only_exact_new_change_metadata(tmp_path, monkeypatch, target):
    change = "openspec/changes/example"
    if target == "existing-root":
        (tmp_path / change).mkdir(parents=True)
    resolution = resolve_report(
        monkeypatch,
        official_report(gaps=("openspec_active_change_missing",)),
        root=tmp_path,
        paths=(f"{change}/.openspec.yaml" if target == "metadata" else change,),
    )
    assert resolution.verdict == ("pass" if target == "metadata" else "block")
    if target == "metadata":
        assert resolution.scope.material_scope["authorized_paths"] == [f"{change}/.openspec.yaml"]
        assert resolution.next_action == "openspec new change example --json"
    elif target == "absent-root":
        assert resolution.scope.material_scope["state"] == "official_change_bootstrap_intent"
        assert resolution.required_gaps == ("openspec_change_metadata_prewrite_required:example",)
        assert resolution.next_action == (
            f"ethos lane prewrite --paths {change}/.openspec.yaml "
            f"--editor-root {tmp_path} --require-editor-root --root {tmp_path} --json"
        )
    else:
        assert resolution.required_gaps == ("openspec_active_change_missing",)
        assert not resolution.scope.material_scope.get("authorized_paths")


@pytest.mark.parametrize("target", ["metadata", "absent-root", "existing-root"])
def test_new_change_bootstrap_coexists_with_other_active_changes(tmp_path, monkeypatch, target):
    """An exact new carrier may bootstrap without selecting an unrelated active Change."""
    change = "openspec/changes/fresh"
    if target == "existing-root":
        (tmp_path / change).mkdir(parents=True)
    report = official_report(gaps=("openspec_active_change_ambiguous:first,second",))
    report["commands"]["list"]["json"] = {"changes": [{"name": "first"}, {"name": "second"}]}
    report["lifecycle"]["changes"] = [{"name": "first"}, {"name": "second"}]

    resolution = resolve_report(
        monkeypatch,
        report,
        root=tmp_path,
        paths=(f"{change}/.openspec.yaml" if target == "metadata" else change,),
    )

    assert resolution.verdict == ("pass" if target == "metadata" else "block")
    if target == "metadata":
        assert resolution.scope.material_scope["authorized_paths"] == [f"{change}/.openspec.yaml"]
        assert resolution.next_action == "openspec new change fresh --json"
    elif target == "absent-root":
        assert resolution.required_gaps == ("openspec_change_metadata_prewrite_required:fresh",)
    else:
        assert not resolution.scope.material_scope.get("authorized_paths")


def test_new_change_bootstrap_does_not_override_an_explicit_other_change(
    tmp_path, monkeypatch
) -> None:
    """An explicit current Change cannot silently authorize a different new Change."""
    monkeypatch.setenv("ETHOS_CHANGE", "first")
    report = official_report(gaps=("openspec_active_change_ambiguous:first,second",))
    report["commands"]["list"]["json"] = {"changes": [{"name": "first"}, {"name": "second"}]}

    resolution = resolve_report(
        monkeypatch,
        report,
        root=tmp_path,
        paths=("openspec/changes/fresh/.openspec.yaml",),
    )

    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")


def test_exact_new_metadata_precedes_unfinished_other_change(monkeypatch, tmp_path) -> None:
    """An incomplete neighbor cannot capture a new Change's metadata intent."""
    report = official_report(
        change="first",
        gaps=("openspec_status_incomplete:first",),
        artifacts=(official_artifact("proposal", "proposal.md", status="ready"),),
    )
    metadata = "openspec/changes/second/.openspec.yaml"

    resolution = resolve_report(monkeypatch, report, root=tmp_path, paths=(metadata,))

    assert resolution.verdict == "pass"
    assert resolution.scope.material_scope["authorized_paths"] == [metadata]
    assert resolution.next_action == "openspec new change second --json"


@pytest.mark.parametrize(
    "rows",
    [
        [{"name": "fresh"}],
        [{"name": "first"}, {"name": "first"}],
        [{"name": "Invalid"}],
        [{}],
    ],
)
def test_new_change_bootstrap_rejects_existing_or_invalid_official_rows(
    monkeypatch, tmp_path, rows
) -> None:
    """Absent paths do not make malformed or already-listed identities new."""
    report = official_report(gaps=("openspec_active_change_ambiguous:first,second",))
    report["commands"]["list"]["json"] = {"changes": rows}

    resolution = resolve_report(
        monkeypatch,
        report,
        root=tmp_path,
        paths=("openspec/changes/fresh/.openspec.yaml",),
    )

    assert resolution.verdict == "block"
    assert not resolution.scope.material_scope.get("authorized_paths")


def test_current_resolution_admits_remaining_official_artifact_after_partial_compilation(
    monkeypatch,
) -> None:
    change = "example"
    tasks = f"openspec/changes/{change}/tasks.md"
    report = official_report(
        change=change,
        gaps=(
            f"openspec_status_incomplete:{change}",
            f"openspec_artifact_incomplete:{change}:tasks",
        ),
        artifacts=(
            official_artifact("proposal", "proposal.md"),
            official_artifact("tasks", "tasks.md", status="ready", requires=("proposal",)),
        ),
        commitment={"schema_version": 1, "id": change, "acceptance": []},
    )
    resolution = resolve_report(monkeypatch, report, paths=(tasks,))
    assert resolution.verdict == "pass"
    assert resolution.scope.material_scope["state"] == "official_change_bootstrap"
    assert resolution.next_action == f"openspec instructions tasks --change {change} --json"


@pytest.mark.parametrize(
    "paths",
    [
        ("openspec/changes/example/.openspec.yaml", "openspec/changes/example/proposal.md"),
        ("openspec/changes/Invalid/.openspec.yaml",),
        ("openspec/changes/archive/.openspec.yaml",),
        ("other/example/.openspec.yaml",),
    ],
)
def test_current_resolution_rejects_ambiguous_or_invalid_new_change_bootstrap(
    monkeypatch,
    paths: tuple[str, ...],
) -> None:
    resolution = resolve_report(
        monkeypatch,
        official_report(gaps=("openspec_active_change_missing",)),
        paths=paths,
    )
    assert resolution.verdict == "block"
    assert resolution.required_gaps == ("openspec_active_change_missing",)


@pytest.mark.parametrize(
    "fault",
    [
        "not-prewrite",
        "complete-invalid",
        "non-object",
        "missing-output",
        "missing-requires",
        "not-ready",
    ],
)
def test_current_resolution_keeps_incomplete_or_invalid_artifact_authority_bounded(
    monkeypatch, fault
):
    artifact = official_artifact("proposal", "proposal.md", status="ready")
    if fault == "complete-invalid":
        artifact["status"] = "done"
    elif fault in {"missing-output", "missing-requires"}:
        artifact.pop("outputPath" if fault == "missing-output" else "requires")
    elif fault == "not-ready":
        artifact["status"] = "blocked"
    report = official_report(
        change="example",
        gaps=(
            "commitment_invalid:example"
            if fault == "complete-invalid"
            else "openspec_status_incomplete:example",
        ),
        artifacts=(None if fault == "non-object" else artifact,),
    )
    resolution = resolve_report(
        monkeypatch,
        report,
        paths=()
        if fault in {"not-prewrite", "not-ready"}
        else ("openspec/changes/example/proposal.md",),
    )
    assert resolution.verdict == "block"
    assert resolution.commitment is None
    assert list(resolution.required_gaps) == report["required_gaps"]
    assert not resolution.scope.material_scope.get("authorized_paths")
    if fault in {"not-prewrite", "not-ready"}:
        expected = "instructions proposal" if fault == "not-prewrite" else "status"
        assert resolution.next_action == f"openspec {expected} --change example --json"
