from __future__ import annotations

import subprocess
from pathlib import Path  # noqa: TC003

from ethos.adapters import openspec


def test_run_json_records_parse_errors_and_non_object_payloads(tmp_path: Path, monkeypatch) -> None:
    class Completed:
        returncode = 7
        stdout = "[1, 2]"
        stderr = "bad"

    calls: list[tuple[str, ...]] = []

    def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
        calls.append(tuple(command))
        assert kwargs["cwd"] == tmp_path
        assert kwargs["timeout"] == 120
        return Completed()

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = openspec._run_json(tmp_path, ("openspec",), ("list", "--json"))

    assert calls == [("openspec", "list", "--json")]
    assert result["exit_code"] == 7
    assert result["json"] == {}
    assert result["parse_error"] == "openspec_json_not_object"

    Completed.stdout = "not-json"
    result = openspec._run_json(tmp_path, ("openspec",), ("doctor", "--json"))
    assert "Expecting value" in result["parse_error"]


def test_selection_and_validation_helper_edge_cases() -> None:
    assert openspec._selected_change({"changes": "bad"}, None) is None
    assert openspec._selected_change({"changes": [{"name": "only"}]}, None) == "only"
    assert (
        openspec._selected_change(
            {
                "changes": [
                    {"name": "older", "lastModified": "2026-01-01"},
                    {"name": "newer", "lastModified": "2026-02-01"},
                ]
            },
            None,
        )
        == "newer"
    )
    assert openspec._selected_change({}, "requested") == "requested"
    assert openspec._validation_failures({"items": "bad"}) == ["openspec_validation_unreadable"]
    assert openspec._validation_failures({"items": [{"valid": False, "type": "change", "id": "x"}, "skip"]}) == [
        "openspec_validation_failed:change:x"
    ]


def test_completed_active_changes_report_handles_missing_cli_and_bad_list(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "repo"
    (root / "openspec").mkdir(parents=True)

    monkeypatch.setattr(openspec, "_openspec_base_command", lambda: None)
    report = openspec.completed_active_changes_report(root)
    assert report["ok"] is False
    assert report["required_gaps"] == ["openspec_official_cli_missing"]

    monkeypatch.setattr(openspec, "_openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec,
        "_run_json",
        lambda *_args: {
            "command": ["openspec", "list", "--json"],
            "exit_code": 1,
            "stdout": "bad",
            "stderr": "boom",
            "json": {},
            "parse_error": "nope",
        },
    )
    report = openspec.completed_active_changes_report(root)
    assert report["completed_changes"] == []
    assert report["required_gaps"] == ["openspec_list_failed", "openspec_list_json_parse_failed"]


def test_archive_closeout_reports_all_edge_gaps(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    archive = root / "openspec" / "changes" / "archive" / "bad_name"
    archive.mkdir(parents=True)
    (archive / ".openspec.yaml").write_text(
        "schema: wrong\ncreated: not-a-date\n", encoding="utf-8"
    )
    (archive / "proposal.md").write_text("# Proposal\n", encoding="utf-8")
    (archive / "design.md").write_text("   \n", encoding="utf-8")
    (archive / "tasks.md").write_text("No checkboxes here\n", encoding="utf-8")

    report = openspec.openspec_archive_closeout_report(root)

    assert report["ok"] is False
    gaps = set(report["required_gaps"])
    assert "openspec_archive_name_invalid:bad_name" in gaps
    assert "openspec_archive_metadata_schema_invalid:bad_name" in gaps
    assert "openspec_archive_metadata_created_invalid:bad_name" in gaps
    assert "openspec_archive_design_empty:bad_name" in gaps
    assert "openspec_archive_tasks_no_checkboxes:bad_name" in gaps
    assert "openspec_archive_delta_specs_missing:bad_name" in gaps


def test_archive_metadata_created_after_archive_and_delta_detail_gaps(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    archive = root / "openspec" / "changes" / "archive" / "2026-07-01-sample"
    spec = archive / "specs" / "capability" / "spec.md"
    spec.parent.mkdir(parents=True)
    for name in ("proposal.md", "design.md"):
        (archive / name).write_text("# ok\n", encoding="utf-8")
    (archive / ".openspec.yaml").write_text(
        "schema: spec-driven\ncreated: 2026-08-01\n", encoding="utf-8"
    )
    (archive / "tasks.md").write_text("- [x] done\n", encoding="utf-8")
    spec.write_text("# Missing OpenSpec delta markers\n", encoding="utf-8")

    report = openspec.openspec_archive_closeout_report(root)
    gaps = set(report["required_gaps"])

    assert "openspec_archive_metadata_created_after_archive:2026-07-01-sample" in gaps
    assert "openspec_archive_delta_header_missing:2026-07-01-sample" in gaps
    assert "openspec_archive_delta_requirement_missing:2026-07-01-sample" in gaps
    assert "openspec_archive_delta_scenario_missing:2026-07-01-sample" in gaps


def test_proposal_protocol_accepts_multiline_metadata_and_reports_profile_fields(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    change = root / "openspec" / "changes" / "sample-change"
    capability = root / "openspec" / "specs" / "sample-capability"
    change.mkdir(parents=True)
    capability.mkdir(parents=True)
    (capability / "spec.md").write_text("# spec\n", encoding="utf-8")
    (capability / "capability.toml").write_text(
        "family = ''\n[owner]\npackage = ''\n[proof_profile]\ndefault_command = ''\n",
        encoding="utf-8",
    )
    (change / "proposal.md").write_text(
        "\n".join(  # noqa: FLY002
            [
                "## Capabilities",
                "- `sample-capability`: subject=repo; reuse=extend; change=rename;",
                "  facet:lifecycle=proof; facet:surface=openspec; facet:authority=claim",
                "",
                "## Out-of-Scope",
                "- provider truth centers",
            ]
        ),
        encoding="utf-8",
    )

    report = openspec._proposal_protocol_report(root, "sample-change")

    assert report["out_of_scope"] is True
    assert report["capabilities"][0]["metadata"]["facet:surface"] == "openspec"
    gaps = set(report["required_gaps"])
    assert "openspec_capability_profile_field_missing:sample-change:sample-capability:family" in gaps
    assert "openspec_capability_profile_field_missing:sample-change:sample-capability:routing_question" in gaps
    assert "openspec_capability_profile_field_missing:sample-change:sample-capability:owner.scope" in gaps
    assert (
        "openspec_capability_profile_field_missing:sample-change:sample-capability:proof_profile.executed_command"
        in gaps
    )


def test_openspec_governance_report_surfaces_command_parse_and_status_failures(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "repo"
    (root / "openspec" / "specs").mkdir(parents=True)
    (root / "openspec" / "config.yaml").write_text("project: sample\n", encoding="utf-8")

    monkeypatch.setattr(openspec, "_openspec_base_command", lambda: ("openspec",))

    def fake_run_json(_root: Path, _base: tuple[str, ...], args: tuple[str, ...]) -> dict[str, object]:
        payload: dict[str, object]
        exit_code = 0
        parse_error = ""
        if args == ("doctor", "--json"):
            payload = {"root": {"healthy": False}}
            parse_error = "bad doctor"
        elif args == ("list", "--json"):
            payload = {"changes": [{"name": "sample", "status": "in-progress"}]}
        elif args == ("status", "--change", "sample", "--json"):
            payload = {"isComplete": False, "schemaName": "spec-driven"}
            parse_error = "bad status"
        elif args == ("validate", "--all", "--strict", "--json"):
            payload = {"items": [{"valid": False, "type": "spec", "id": "cap"}], "summary": {}}
            exit_code = 1
            parse_error = "bad validate"
        else:
            payload = {}
        return {
            "command": ["openspec", *args],
            "exit_code": exit_code,
            "stdout": "{}",
            "stderr": "",
            "json": payload,
            "parse_error": parse_error,
        }

    monkeypatch.setattr(openspec, "_run_json", fake_run_json)

    report = openspec.openspec_governance_report(root)

    gaps = report["required_gaps"]
    assert "openspec_doctor_unhealthy" in gaps
    assert "openspec_status_incomplete:sample" in gaps
    assert "openspec_validation_failed:spec:cap" in gaps
    assert "openspec_doctor_json_parse_failed" in gaps
    assert "openspec_status_json_parse_failed" in gaps
    assert "openspec_validate_json_parse_failed" in gaps
