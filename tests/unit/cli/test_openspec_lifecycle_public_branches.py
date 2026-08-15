from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

import ethos.adapters.openspec.governance as governance
import ethos.adapters.openspec.lifecycle.archive_binding as binding
import ethos.adapters.openspec.lifecycle.archive_transition as transition
import ethos.adapters.openspec.lifecycle.report as report
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile
from tests.support.semantic import commitment_v2

if TYPE_CHECKING:
    from ethos.contracts.semantic import Commitment


def _completed(name: str = "change") -> dict[str, object]:
    return {"name": name, "status": "complete", "completedTasks": 1, "totalTasks": 1}


def _result(*, returncode: int = 0, stdout: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")


def _commitment(scope: tuple[str, ...] = ("openspec/changes/change/**",)) -> Commitment:
    return commitment_v2(
        id="change:change", intent="Archive exactly.", subjects=("repository:test",), scope=scope
    )


def test_official_rows_selection_and_command_gaps_reject_malformed_authority() -> None:
    assert report.official_change_rows({}) is None
    assert report.official_change_rows({"changes": ["bad"]}) is None
    malformed = [
        {"name": "", "status": "complete", "completedTasks": 1, "totalTasks": 1},
        {"name": "x", "status": "complete", "completedTasks": True, "totalTasks": 1},
        {"name": "x", "status": "complete", "completedTasks": 0, "totalTasks": 1},
    ]
    assert all(report.official_change_rows({"changes": [row]}) is None for row in malformed)
    rows = [_completed("first"), _completed("second")]
    normalized = report.official_change_rows({"changes": rows})
    assert normalized is not None
    assert report.selection_gaps(normalized, "missing") == [
        "openspec_requested_change_missing:missing"
    ]
    assert report.selection_gaps(normalized, None) == [
        "openspec_active_change_ambiguous:first,second"
    ]

    def result(**updates: object) -> dict[str, object]:
        return {"exit_code": 0, "json": {}, "parse_error": "", **updates}

    gaps = report.openspec_command_gaps(
        doctor=result(json={"root": {"healthy": True}}),
        list_result=result(),
        status=result(parse_error="invalid"),
        validate=result(),
        selected=None,
    )
    assert gaps == ["openspec_status_json_parse_failed"]


def test_edge_reports_and_lifecycle_mismatches_preserve_attribution(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        report.scope,
        "material_change_scope_report",
        lambda *_a, **_k: {"required_gaps": [], "state": "covered"},
    )
    request = report.OpenSpecRequest(change="requested", lifecycle=True)
    context = report.OpenSpecReportContext(
        request=request,
        official_config={"required_gaps": []},
        official_package="@fission-ai/openspec",
        required_gaps=["openspec_official_cli_missing"],
        advisory_gaps=[],
        protected_branch_residue={"verdict": "pass"},
    )
    unavailable = report.openspec_unavailable_report(tmp_path, context)
    timeout = report.openspec_timeout_report(
        root=tmp_path,
        context=context,
        base_command=("node", "openspec.js"),
        doctor={"exit_code": 124},
    )
    assert unavailable["official_cli"]["available"] is False
    assert timeout["commands"]["doctor"] == {"exit_code": 124}
    assert timeout["commands"]["list"] == {}

    status_mismatch = report.lifecycle_report(
        tmp_path,
        request=request,
        list_payload={"changes": [_completed("requested")]},
        status_payload={"changeName": "other"},
        apply_payload={"changeName": "requested"},
    )
    apply_mismatch = report.lifecycle_report(
        tmp_path,
        request=request,
        list_payload={"changes": [_completed("requested")]},
        status_payload={"changeName": "requested"},
        apply_payload={"changeName": "other"},
    )
    assert status_mismatch["required_gaps"] == ["openspec_status_change_mismatch:requested"]
    assert apply_mismatch["required_gaps"] == ["openspec_apply_change_mismatch:requested"]


def test_public_lifecycle_filters_capability_escape_and_governance_rejects_invalid_identifier(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root, openspec={"material_paths": ["openspec/**"]})
    (root / "openspec/specs").mkdir(parents=True)
    prefix = root / "openspec/changes/valid-change/specs"
    inside = prefix / "contracts/spec.md"
    outside = root / "openspec/specs/contracts/spec.md"
    monkeypatch.setattr(report.scope, "commitment_report", lambda *_args: {"required_gaps": []})

    lifecycle = report.lifecycle_report(
        root,
        request=report.OpenSpecRequest(change="valid-change", lifecycle=True),
        list_payload={"changes": [_completed("valid-change")]},
        status_payload={
            "changeName": "valid-change",
            "artifactPaths": {"specs": {"existingOutputPaths": [str(outside), str(inside)]}},
            "artifacts": [],
        },
        apply_payload={"changeName": "valid-change"},
    )
    result = governance.openspec_governance_report(root, change="20260810-invalid")

    assert lifecycle["changes"][0]["capabilities"] == ["contracts"]
    assert result["lifecycle"]["changes"] == []
    assert result["required_gaps"] == ["openspec_active_change_identifier_invalid:20260810-invalid"]


def test_archive_transition_environment_rejects_extra_keys_and_stale_bindings(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(transition, "current_tree", lambda *_a: "head-tree")
    monkeypatch.setattr(transition, "current_tracked_head", lambda _root: "head")
    monkeypatch.setattr(transition, "run_git", lambda *_a, **_k: _result(stdout="index-tree\n"))
    raw = transition.archive_transition_environment(
        tmp_path,
        change="change",
        head="head",
        changed_paths=("archive",),
        official_change_complete=True,
        completion_artifacts=("tasks.md",),
    )["ETHOS_ARCHIVE_TRANSITION"]
    payload = json.loads(raw)
    payload["unexpected"] = True
    monkeypatch.setenv("ETHOS_ARCHIVE_TRANSITION", json.dumps(payload))
    assert (
        transition.archive_transition_facts(
            tmp_path, changed_paths=("archive",), requested_change="change"
        )
        is None
    )
    monkeypatch.setenv("ETHOS_ARCHIVE_TRANSITION", raw)
    assert (
        transition.archive_transition_facts(
            tmp_path, changed_paths=("different",), requested_change="change"
        )
        is None
    )


def test_archive_context_and_binding_fail_closed_on_role_lease_and_commitment_errors(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(binding, "git_stdout", lambda *_a: "work/change")
    monkeypatch.setattr(
        binding,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(role_for_branch=lambda _b: "work_lane"),
    )
    monkeypatch.setattr(
        binding, "leases_by_branch", lambda _root: {"work/change": {"lease_state": "expired"}}
    )
    assert binding.archive_context(tmp_path) is None

    lease = {"lease_state": "valid", "commitment_binding": "bound", "expected_head": "work/change"}
    monkeypatch.setattr(binding, "leases_by_branch", lambda _root: {"work/change": lease})
    monkeypatch.setattr(
        binding,
        "load_lease_bound_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("invalid")),
    )
    assert binding.archive_context(tmp_path) is None

    monkeypatch.setattr(binding, "current_tree", lambda *_a: "head-tree")
    monkeypatch.setattr(binding, "run_git", lambda *_a, **_k: _result(stdout="index-tree\n"))
    monkeypatch.setattr(
        binding, "active_commitments", lambda *_a: ("openspec/changes/change/commitment.toml",)
    )
    monkeypatch.setattr(
        binding,
        "exact_commitment_fields",
        lambda *_a, **_k: {
            "base_commitment_path": "openspec/changes/change/commitment.toml",
            "base_commitment_bytes_sha256": "bytes",
            "base_commitment_digest": "digest",
            "expected_tree": "index-tree",
        },
    )
    assert binding.archive_binding(
        tmp_path,
        head="head",
        change="change",
        lease={
            "base_commitment_path": "openspec/changes/change/commitment.toml",
            "base_commitment_bytes_sha256": "bytes",
            "base_commitment_digest": "digest",
        },
    ) == ("completion_transition", "index-tree", "openspec/changes/change/commitment.toml")


def test_archive_binding_helpers_reject_unreadable_ambiguous_and_invalid_dates(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(binding, "run_git", lambda *_a, **_k: _result(returncode=1))
    with pytest.raises(ValueError, match="openspec_archive_tree_unreadable"):
        binding.staged_archive_carrier(
            tmp_path,
            head="head",
            tree="tree",
            lease={},
            change="change",
        )
    assert binding.active_commitments(tmp_path, "tree") == ("unreadable",)
    assert not binding.valid_archive_carrier(
        "openspec/changes/archive/2026-99-99-change/commitment.toml", "change"
    )


def test_bound_archive_history_and_exact_relocation_preserve_semantic_identity(
    monkeypatch, tmp_path: Path
) -> None:
    source = "openspec/changes/change/commitment.toml"
    carrier = "openspec/changes/archive/2026-08-10-change/commitment.toml"
    values = {
        ("rev-parse", "head:" + source): "source-blob",
        ("rev-list", "head", "--", source, carrier): "revision",
        ("rev-parse", "parent:" + source): "source-blob",
        ("rev-parse", "revision:" + carrier): "source-blob",
        ("rev-parse", "revision:" + source): "",
    }
    monkeypatch.setattr(binding, "git_stdout", lambda _r, *args: values.get(args, ""))
    monkeypatch.setattr(
        binding,
        "run_git",
        lambda *_a, **_k: _result(stdout="revision parent\n"),
    )
    monkeypatch.setattr(binding, "current_tree", lambda *_a: "tree")
    assert binding.exact_carrier_relocation(tmp_path, "parent", "revision", source, carrier)
    assert binding.bound_archive_binding(
        tmp_path, head="head", change="change", carrier=carrier
    ) == ("post_archive_closeout", "tree", carrier)


def test_archive_scope_attribution_maps_archive_and_proven_canonical_specs(
    monkeypatch, tmp_path: Path
) -> None:
    carrier = "openspec/changes/archive/2026-08-10-change/commitment.toml"
    profile = SimpleNamespace(
        state="valid",
        declaration=SimpleNamespace(openspec=SimpleNamespace(material_paths=("openspec/**",))),
    )
    monkeypatch.setattr(transition, "load_repository_profile", lambda _root: profile)
    monkeypatch.setattr(
        transition,
        "git_stdout",
        lambda _root, *args: (
            "work/change"
            if args == ("branch", "--show-current")
            else "blob"
            if args[-1].endswith("/specs/contracts/spec.md")
            else ""
        ),
    )
    scope = (
        "openspec/changes/change/**",
        "openspec/changes/change/specs/contracts/spec.md",
    )
    commitment = _commitment(scope)
    lease = {
        "lease_state": "valid",
        "expected_head": "head",
        "base_commitment_digest": commitment.digest(),
    }
    monkeypatch.setattr(transition, "archive_context", lambda _root: ("head", lease, commitment))
    monkeypatch.setattr(
        transition,
        "archive_binding",
        lambda *_args, **_kwargs: ("archive_transition", "tree", carrier),
    )
    monkeypatch.setattr(transition, "load_commitment", lambda *_args, **_kwargs: commitment)
    monkeypatch.setattr(transition, "active_commitments", lambda *_args: ())
    result = transition.lease_bound_archive_scope_report(
        tmp_path,
        requested_change="change",
        official_change_complete=True,
        changed_paths=(
            "openspec/changes/archive/2026-08-10-change/tasks.md",
            "openspec/specs/contracts/spec.md",
            "openspec/specs/unproven/spec.md",
        ),
        completion_artifacts=("openspec/changes/change/specs/contracts/spec.md",),
    )
    assert result is not None
    assert result["covered_paths"] == [
        {
            "path": "openspec/changes/archive/2026-08-10-change/tasks.md",
            "changes": ["change"],
        },
        {"path": "openspec/specs/contracts/spec.md", "changes": ["change"]},
    ]
    assert result["uncovered_paths"] == ["openspec/specs/unproven/spec.md"]

    monkeypatch.setattr(
        transition,
        "archive_binding",
        lambda *_args, **_kwargs: ("completion_transition", "tree", carrier),
    )
    monkeypatch.setattr(transition, "active_commitments", lambda *_args: (carrier,))
    fallback = transition.lease_bound_archive_scope_report(
        tmp_path,
        requested_change="change",
        official_change_complete=True,
        changed_paths=("README.md",),
        completion_artifacts=("README.md",),
    )

    assert fallback is not None
    assert fallback["material_paths"] == []
    assert fallback["covered_paths"] == []
