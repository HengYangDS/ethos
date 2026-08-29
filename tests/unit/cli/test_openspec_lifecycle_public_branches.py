from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import ethos.adapters.openspec.governance as governance
import ethos.adapters.openspec.lifecycle.report as report
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile


def _completed(name: str = "change") -> dict[str, object]:
    return {"name": name, "status": "complete", "completedTasks": 1, "totalTasks": 1}


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
    tmp_path: Path,
) -> None:
    root = init_git_repo(tmp_path / "repo")
    write_test_profile(root, openspec={"material_paths": ["openspec/**"]})
    (root / "openspec/specs").mkdir(parents=True)
    prefix = root / "openspec/changes/valid-change/specs"
    inside = prefix / "contracts/spec.md"
    outside = root / "openspec/specs/contracts/spec.md"
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
