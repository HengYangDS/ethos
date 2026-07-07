"""Coverage-closure v3: openspec reachable branches (100% no-exemption)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.openspec import archive as archive_mod
from ethos.adapters.openspec import openspec
from ethos.adapters.openspec import proposal
from ethos.repository import audit_openspec
from ethos.repository import openspec_metadata
from ethos_core.contracts.branch_roles import ROLE_RELEASE_ROOT
from ethos_core.contracts.branch_roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    import pytest

# --- adapters/openspec.py ----------------------------------------------------


def test_run_json_skips_parse_when_stdout_empty(tmp_path: Path) -> None:
    # Empty stdout leaves the JSON parse block unentered (branch 77->87).
    result = openspec._run_json(tmp_path, (sys.executable,), ("-c", "pass"))
    assert result["json"] == {}
    assert result["parse_error"] == ""
    assert result["exit_code"] == 0


def test_validation_failures_skips_valid_item() -> None:
    # A dict item whose `valid` is not False loops back without appending (branch 125->122).
    assert openspec._validation_failures({"items": [{"valid": True}]}) == []


def test_governance_report_returns_cli_missing_when_no_base_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No official CLI drives the early delegating return (line 138).
    monkeypatch.setattr(openspec, "_openspec_base_command", lambda: None)
    result = openspec.openspec_governance_report(tmp_path)
    assert result["official_cli"]["available"] is False
    assert "openspec_official_cli_missing" in result["required_gaps"]


def test_completed_active_change_names_non_list() -> None:
    # A non-list `changes` payload short-circuits to an empty list (line 197).
    assert openspec._completed_active_change_names({"changes": 123}) == []


def test_archive_closeout_issues_skips_task_issues_without_tasks_file(tmp_path: Path) -> None:
    # An archive with no tasks.md skips the task-issue extension and still runs the
    # delta-issue extension (branch 287->289).
    archive = tmp_path / "2026-01-01-sample"
    archive.mkdir()
    codes = {
        issue["code"] for issue in archive_mod._archive_closeout_issues(archive, root=tmp_path)
    }
    assert "openspec_archive_tasks_missing" in codes
    assert "openspec_archive_tasks_no_checkboxes" not in codes
    assert "openspec_archive_delta_specs_missing" in codes


def test_archive_delta_issues_specs_dir_without_spec_files(tmp_path: Path) -> None:
    # A present-but-empty specs directory yields the delta-specs-missing gap (line 391).
    specs_root = tmp_path / "specs"
    specs_root.mkdir()
    issues = archive_mod._archive_delta_issues(
        specs_root, archive_name="2026-01-01-x", root=tmp_path
    )
    assert [issue["code"] for issue in issues] == ["openspec_archive_delta_specs_missing"]


def test_workspace_signature_empty_without_openspec_dir(tmp_path: Path) -> None:
    # A root with no openspec/ directory yields an empty signature (line 446).
    assert openspec._openspec_workspace_signature(tmp_path) == ()


def test_active_claim_carriers_skips_inactive_and_empty_carrier(tmp_path: Path) -> None:
    # Inactive claim -> continue (line 586); active claim with empty carrier -> loop
    # back without adding (branch 588->582); active claim with a carrier is collected.
    claims_dir = tmp_path / "evidence" / "claims"
    claims_dir.mkdir(parents=True)
    (claims_dir / "retired.toml").write_text('[claim]\nstate = "retired"\n', encoding="utf-8")
    (claims_dir / "empty.toml").write_text(
        '[claim]\nstate = "active"\n[carriers]\nopenspec = ""\n', encoding="utf-8"
    )
    (claims_dir / "bound.toml").write_text(
        '[claim]\nstate = "active"\n[carriers]\nopenspec = "openspec/changes/foo/proposal.md"\n',
        encoding="utf-8",
    )
    assert openspec._active_claim_openspec_carriers(tmp_path) == {
        "openspec/changes/foo/proposal.md"
    }


def test_lifecycle_report_non_list_changes_yields_no_change_names(tmp_path: Path) -> None:
    # No selected change and a non-list `changes` payload takes the else branch (line 632).
    report = openspec._lifecycle_report(
        tmp_path, selected_change=None, list_payload={"changes": 5}, enabled=True
    )
    assert report["changes"] == []
    assert report["required_gaps"] == []


def test_proposal_capability_entries_flushes_previous_capability() -> None:
    # A second capability line flushes the in-progress capability first (line 723).
    text = "- `cap-one`: subject=a; reuse=new\n- `cap-two`: subject=b; reuse=extend\n"
    entries = proposal._proposal_capability_entries(text)
    assert [entry["capability"] for entry in entries] == ["cap-one", "cap-two"]


def test_proposal_capability_entry_skips_part_without_equals() -> None:
    # A metadata part lacking `=` is skipped (line 742).
    entry = proposal._proposal_capability_entry("cap", "subject=a; noequals; reuse=new")
    assert entry["metadata"] == {"subject": "a", "reuse": "new"}


# --- repository/audit_openspec.py --------------------------------------------


def test_required_gaps_filters_non_blocked_role_and_empty_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A record whose role is not blocked loops back (branch 84->81); a blocked-role
    # record with an empty gap loops back without appending (branch 86->81); only the
    # blocked-role record with a gap is returned.
    def _fake_report(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "records": [
                {"branch": "wl", "role": ROLE_WORK_LANE, "change": "c1", "gap": "g1"},
                {"branch": "m", "role": ROLE_RELEASE_ROOT, "change": "c2", "gap": ""},
                {"branch": "m", "role": ROLE_RELEASE_ROOT, "change": "c3", "gap": "g3"},
            ]
        }

    monkeypatch.setattr(audit_openspec, "protected_branch_active_change_report", _fake_report)
    gaps = audit_openspec.protected_branch_active_change_required_gaps(
        Path("/nonexistent"), current_branch="work/x"
    )
    assert gaps == ["g3"]


# --- repository/openspec_metadata.py -----------------------------------------


def test_read_metadata_skips_non_matching_line(tmp_path: Path) -> None:
    # A non-empty, non-comment line that does not match the key pattern loops back
    # without recording metadata (branch 40->35).
    path = tmp_path / ".openspec.yaml"
    path.write_text(
        "# a comment\nschema: spec-driven\nplain prose without a key colon\n", encoding="utf-8"
    )
    assert openspec_metadata.read_openspec_metadata(path) == {"schema": "spec-driven"}
