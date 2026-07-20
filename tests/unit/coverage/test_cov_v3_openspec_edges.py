"""Coverage-closure v3: openspec reachable branches (100% no-exemption)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.openspec.archive.core as archive_mod
import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.openspec.core as openspec_core
import ethos.adapters.openspec.lifecycle.core as openspec_lifecycle
import ethos.adapters.openspec.metadata.core as openspec_metadata_adapter
import ethos.adapters.openspec.protocol.core as proposal
import ethos.adapters.openspec.workspace.core as openspec_workspace
import ethos.repository.openspec.audit as openspec_audit
import ethos.repository.openspec.audit as openspec_audit_core
import ethos.repository.openspec.metadata as openspec_metadata
from ethos_core.contracts.branch.roles import ROLE_RELEASE_ROOT
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE

if TYPE_CHECKING:
    import pytest


def test_run_json_skips_parse_when_stdout_empty(tmp_path: Path) -> None:
    script = tmp_path / "empty.py"
    script.write_text("", encoding="utf-8")
    result = openspec_cli.run_json(tmp_path, (sys.executable,), (str(script),))
    assert result["json"] == {}
    assert result["parse_error"] == ""
    assert result["exit_code"] == 0


def test_version_key_extracts_numeric_components() -> None:
    assert openspec_cli.version_key("1.20.beta3") == (1, 20, 3)


def test_validation_failures_skips_valid_item() -> None:
    assert openspec_lifecycle.validation_failures({"items": [{"valid": True}]}) == []


def test_governance_report_returns_cli_missing_when_no_base_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: None)
    result = openspec_core.openspec_governance_report(tmp_path)
    assert result["official_cli"]["available"] is False
    assert "openspec_official_cli_missing" in result["required_gaps"]


def test_completed_active_change_names_non_list() -> None:
    assert openspec_metadata_adapter.completed_active_change_names({"changes": 123}) == []


def test_archive_closeout_issues_skips_task_issues_without_tasks_file(tmp_path: Path) -> None:
    archive = tmp_path / "2026-01-01-sample"
    archive.mkdir()
    codes = {issue["code"] for issue in archive_mod.archive_closeout_issues(archive, root=tmp_path)}
    assert "openspec_archive_tasks_missing" in codes
    assert "openspec_archive_tasks_no_checkboxes" not in codes
    assert "openspec_archive_delta_specs_missing" in codes


def test_archive_delta_issues_specs_dir_without_spec_files(tmp_path: Path) -> None:
    specs_root = tmp_path / "specs"
    specs_root.mkdir()
    issues = archive_mod.archive_delta_issues(specs_root, archive_name="2026-01-01-x", root=tmp_path)  # fmt: skip
    assert [issue["code"] for issue in issues] == ["openspec_archive_delta_specs_missing"]


def test_workspace_signature_empty_without_openspec_dir(tmp_path: Path) -> None:
    assert openspec_workspace.openspec_workspace_signature(tmp_path) == ()


def test_workspace_signature_includes_missing_profile_when_openspec_exists(tmp_path: Path) -> None:
    """The profile companion invalidates cached lifecycle results after creation."""
    (tmp_path / "openspec").mkdir()
    assert openspec_workspace.openspec_workspace_signature(tmp_path) == ((".ethos/profile.toml", -1, -1),)  # fmt: skip


def test_active_claim_carriers_skips_inactive_and_empty_carrier(tmp_path: Path) -> None:
    claims_dir = tmp_path / "evidence" / "claims"
    claims_dir.mkdir(parents=True)
    (claims_dir / "retired.toml").write_text('[claim]\nstate = "retired"\n', encoding="utf-8")
    (claims_dir / "empty.toml").write_text('[claim]\nstate = "active"\n[carriers]\nopenspec = ""\n', encoding="utf-8")  # fmt: skip
    (claims_dir / "bound.toml").write_text('[claim]\nstate = "active"\n[carriers]\nopenspec = "openspec/changes/foo/proposal.md"\n', encoding="utf-8")  # fmt: skip
    assert openspec_lifecycle.active_claim_openspec_carriers(tmp_path) == {"openspec/changes/foo/proposal.md"}  # fmt: skip


def test_lifecycle_report_non_list_changes_yields_no_change_names(tmp_path: Path) -> None:
    report = openspec_lifecycle.lifecycle_report(tmp_path, request=openspec_lifecycle.OpenSpecRequest(change=None, lifecycle=True), list_payload={"changes": 5})  # fmt: skip
    assert report["changes"] == []
    assert report["required_gaps"] == []


def test_proposal_capability_entries_flushes_previous_capability() -> None:
    text = "- `cap-one`: subject=a; reuse=new\n- `cap-two`: subject=b; reuse=extend\n"
    entries = proposal.proposal_capability_entries(text)
    assert [entry["capability"] for entry in entries] == ["cap-one", "cap-two"]


def test_proposal_capability_entry_skips_part_without_equals() -> None:
    entry = proposal.proposal_capability_entry("cap", "subject=a; noequals; reuse=new")
    assert entry["metadata"] == {"subject": "a", "reuse": "new"}


def test_required_gaps_filters_non_blocked_role_and_empty_gap(monkeypatch: pytest.MonkeyPatch) -> None:  # fmt: skip

    def _fake_report(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {"records": [{"branch": "wl", "role": ROLE_WORK_LANE, "change": "c1", "gap": "g1"}, {"branch": "m", "role": ROLE_RELEASE_ROOT, "change": "c2", "gap": ""}, {"branch": "m", "role": ROLE_RELEASE_ROOT, "change": "c3", "gap": "g3"}]}  # fmt: skip

    monkeypatch.setattr(openspec_audit, "protected_branch_active_change_report", _fake_report)
    gaps = openspec_audit_core.protected_branch_active_change_required_gaps(Path("/nonexistent"), current_branch="work/x")  # fmt: skip
    assert gaps == ["g3"]


def test_read_metadata_skips_non_matching_line(tmp_path: Path) -> None:
    path = tmp_path / ".openspec.yaml"
    path.write_text("# a comment\nschema: spec-driven\nplain prose without a key colon\n", encoding="utf-8")  # fmt: skip
    assert openspec_metadata.read_openspec_metadata(path) == {"schema": "spec-driven"}


def test_openspec_remaining_short_circuits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ETHOS_OPENSPEC_BIN", "custom-openspec")
    assert openspec_cli.openspec_base_command() == ("custom-openspec",)
    cache = tmp_path / "cache"
    package = cache / "x/node_modules/@fission-ai/openspec/package.json"
    package.parent.mkdir(parents=True)
    package.write_text("{", encoding="utf-8")
    for name, payload in (("empty", '{"bin": ""}'), ("missing", '{"bin": "missing.js"}')):
        item = cache / name / "node_modules/@fission-ai/openspec/package.json"
        item.parent.mkdir(parents=True)
        item.write_text(payload, encoding="utf-8")
    monkeypatch.setenv("ETHOS_NPX_CACHE_DIR", str(cache))
    assert openspec_cli.cached_official_cli_entry() is None
    assert openspec_metadata_adapter.completed_active_change_names({"changes": [None]}) == []
    assert proposal.proposal_protocol_report(tmp_path, "missing") == {"ok": True, "required_gaps": [], "capabilities": [], "out_of_scope": False}  # fmt: skip
    profile = tmp_path / "openspec/specs/cap/capability.toml"
    profile.parent.mkdir(parents=True)
    profile.write_text("[", encoding="utf-8")
    assert proposal.capability_profile_gaps(tmp_path, "change", "cap") == ["openspec_capability_profile_invalid:change:cap"]  # fmt: skip
