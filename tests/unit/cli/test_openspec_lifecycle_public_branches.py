"""Native OpenSpec result boundaries and public lifecycle projections."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

import ethos.adapters.openspec.governance as governance
import ethos.adapters.openspec.lifecycle.report as report
from ethos.adapters.openspec.selection import selection_gaps
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile


def _completed(name: str = "change", **updates: object) -> dict[str, object]:
    return {"name": name, "status": "complete", "completedTasks": 1, "totalTasks": 1, **updates}


def _validation_item(**fields: object) -> dict[str, object]:
    return {"id": "native", "type": "change", "valid": True, **fields}


@pytest.mark.parametrize("exit_code", [0, 1])
@pytest.mark.parametrize("parse_error", ["", "malformed", "openspec_command_timeout"])
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"items": []}, []),
        ({"items": [_validation_item()]}, []),
        ({"items": [_validation_item(valid=False)]}, ["openspec_validation_failed:change:native"]),
        *(
            (payload, ["openspec_validation_unreadable"])
            for payload in ({}, {"items": None}, {"items": {}}, {"items": [None]})
        ),
        *(
            ({"items": [_validation_item(**{field: value})]}, ["openspec_validation_unreadable"])
            for field, values in (
                ("id", ("", 1)),
                ("type", ("other", [])),
                ("valid", (1, "false", None)),
            )
            for value in values
        ),
        (
            {
                "items": [
                    _validation_item(
                        issues=[{"level": "INFO", "path": "file", "message": "No delta"}]
                    )
                ]
            },
            [],
        ),
        (
            {
                "items": [
                    _validation_item(
                        id="long",
                        type="spec",
                        issues=[
                            {"level": "INFO", "path": "requirements[0]", "message": "Long text"}
                        ],
                    )
                ]
            },
            ["openspec_validation_issue:INFO:spec:long:requirements[0]"],
        ),
        (
            {
                "report": {
                    "kind": "validation-findings",
                    "version": "1.0",
                    "scope": "all",
                    "returnedItems": 1,
                    "totalItems": 1,
                },
                "itemFindings": [
                    _validation_item(
                        id="long",
                        type="spec",
                        issues=[
                            {"level": "INFO", "path": "requirements[0]", "message": "Long text"}
                        ],
                    )
                ],
            },
            ["openspec_validation_issue:INFO:spec:long:requirements[0]"],
        ),
        (
            {
                "report": {
                    "kind": "validation-findings",
                    "version": "1.0",
                    "scope": "all",
                    "returnedItems": 0,
                    "totalItems": 1,
                },
                "itemFindings": [_validation_item(id="long", type="spec")],
            },
            ["openspec_validation_unreadable"],
        ),
        (
            {
                "items": [
                    _validation_item(id="valid", type="spec"),
                    _validation_item(id="invalid", type="spec", valid=False),
                ]
            },
            ["openspec_validation_failed:spec:invalid"],
        ),
    ],
)
def test_validation_results_preserve_execution_and_item_failures(
    monkeypatch, tmp_path, exit_code, payload, expected, parse_error
) -> None:
    """Neither process success nor missing diagnostics can erase native failure."""
    expected = expected or (["openspec_validate_failed"] if exit_code else [])
    validation = {"exit_code": exit_code, "json": payload, "parse_error": parse_error}
    expected = expected + (["openspec_validate_json_parse_failed"] if parse_error else [])
    monkeypatch.setattr(governance.openspec_cli, "openspec_base_command", lambda: ("native",))
    monkeypatch.setattr(governance.openspec_cli, "run_json", lambda *_args: validation)
    gate = governance.openspec_validation_report(tmp_path)
    assert gate == {
        "verdict": "block" if expected else "pass",
        "required_gaps": expected,
        "validation": validation,
    }
    observed = report.openspec_command_gaps(
        doctor={"exit_code": 0, "json": {"root": {"healthy": True}}, "parse_error": ""},
        list_result={"exit_code": 0, "json": {"changes": []}, "parse_error": ""},
        status={},
        validate=validation,
        selected=None,
    )
    assert observed == expected


def test_official_rows_selection_and_command_gaps_reject_malformed_authority() -> None:
    assert report.official_change_rows({}) is None
    assert report.official_change_rows({"changes": ["bad"]}) is None
    malformed = [
        _completed(""),
        _completed("x", completedTasks=True),
        _completed("x", completedTasks=0),
    ]
    assert all(report.official_change_rows({"changes": [row]}) is None for row in malformed)
    rows = [_completed("first"), _completed("second")]
    normalized = report.official_change_rows({"changes": rows})
    assert normalized is not None
    assert selection_gaps(normalized, "missing") == ["openspec_requested_change_missing:missing"]
    assert selection_gaps(normalized, None) == ["openspec_active_change_ambiguous:first,second"]

    def result(**updates: object) -> dict[str, object]:
        return {"exit_code": 0, "json": {}, "parse_error": "", **updates}

    gaps = report.openspec_command_gaps(
        doctor=result(json={"root": {"healthy": True}}),
        list_result=result(),
        status=result(parse_error="invalid"),
        validate=result(json={"items": []}),
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
        branch_intent={"verdict": "pass"},
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

    for stage in ("status", "apply"):
        payloads = {
            f"{key}_payload": {"changeName": "other" if key == stage else "requested"}
            for key in ("status", "apply")
        }
        mismatch = report.lifecycle_report(
            tmp_path,
            request=request,
            list_payload={"changes": [_completed("requested")]},
            **payloads,
        )
        assert mismatch["required_gaps"] == [f"openspec_{stage}_change_mismatch:requested"]


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
