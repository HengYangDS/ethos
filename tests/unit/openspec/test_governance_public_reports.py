"""Public OpenSpec governance edge reports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as cli
import ethos.adapters.openspec.governance as governance
import tests.support.governed_repository as fixture

if TYPE_CHECKING:
    from pathlib import Path


def _repo(tmp_path: Path) -> Path:
    root = fixture.init_git_repo(tmp_path / "repo")
    fixture.write_test_profile(root, openspec={"material_paths": ["openspec/**"]})
    (root / "openspec/specs").mkdir(parents=True)
    (root / "openspec/config.yaml").write_text("schema: spec-driven\n", encoding="utf-8")
    return root


def _residue(verdict: str = "pass") -> dict[str, object]:
    return {
        "verdict": verdict,
        "records": [],
        "advisory_gaps": [],
        "required_gaps": ["openspec_branch_unavailable:candidate/dev"]
        if verdict == "unknown"
        else [],
        "summary": {"residue_count": 0},
    }


def _receipt(*, payload=None, parse_error="", exit_code=0):
    return {
        "command": ["openspec"],
        "exit_code": exit_code,
        "stdout": "",
        "stderr": "",
        "json": payload or {},
        "parse_error": parse_error,
    }


def test_governance_reports_not_applicable_without_profile(tmp_path):
    root = fixture.init_git_repo(tmp_path / "repo")

    report = governance.openspec_governance_report(root, lifecycle=True)

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "not_applicable",
        [],
    )
    assert report["official_cli"] == {"available": False, "base_command": []}


def test_governance_rejects_archive_and_invalid_active_identifiers(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    (root / "openspec/changes/archive/archived").mkdir(parents=True)
    monkeypatch.setattr(cli, "openspec_base_command", lambda: (_ for _ in ()).throw(AssertionError))

    archived = governance.openspec_governance_report(root, change="archived", lifecycle=True)
    invalid = governance.openspec_governance_report(root, change="20260810-invalid")

    assert archived["required_gaps"] == [
        "openspec_active_change_identifier_is_archive_directory:archived"
    ]
    assert invalid["required_gaps"] == [
        "openspec_active_change_identifier_invalid:20260810-invalid"
    ]
    assert archived["commands"] == {"doctor": {}, "list": {}, "status": {}, "validate": {}}


def test_governance_reports_cli_unavailable_and_optional_absent_workspace(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    monkeypatch.setattr(cli, "openspec_base_command", lambda: None)
    monkeypatch.setattr(
        governance, "protected_branch_active_change_report", lambda *_a, **_k: _residue()
    )

    unavailable = governance.openspec_governance_report(root)
    absent = fixture.init_git_repo(tmp_path / "absent")
    fixture.write_test_profile(absent, openspec={"material_paths": ["docs/**"]})
    not_applicable = governance.openspec_governance_report(absent, require_workspace=False)

    assert unavailable["verdict"] == "block"
    assert "openspec_official_cli_missing" in unavailable["required_gaps"]
    assert (not_applicable["verdict"], not_applicable["state"]) == ("pass", "not_applicable")


def test_governance_reports_timeout(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    monkeypatch.setattr(cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        governance, "protected_branch_active_change_report", lambda *_a, **_k: _residue()
    )

    timeout = _receipt(parse_error="openspec_command_timeout")
    calls = []

    def run_timeout(_root, _base, args):
        calls.append(args)
        return _receipt() if args[:2] == ("config", "list") else timeout

    monkeypatch.setattr(cli, "run_json", run_timeout)
    report = governance.openspec_governance_report(root)
    assert report["verdict"] == "block"
    assert {"openspec_doctor_unhealthy", "openspec_doctor_json_parse_failed"} <= set(
        report["required_gaps"]
    )
    assert calls == [("config", "list", "--json"), ("doctor", "--json")]


def test_governance_reports_malformed_command_payloads(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    malformed = _receipt(parse_error="malformed")
    monkeypatch.setattr(cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        governance, "protected_branch_active_change_report", lambda *_a, **_k: _residue()
    )

    def run_malformed(_root, _base, args):
        if args[:2] == ("config", "list"):
            return malformed
        if args[:1] == ("doctor",):
            return _receipt(payload={"root": {"healthy": True}})
        if args[:1] == ("list",):
            return _receipt(payload={"changes": []}, parse_error="malformed")
        if args[:1] == ("validate",):
            return malformed
        return _receipt()

    monkeypatch.setattr(cli, "run_json", run_malformed)
    malformed_report = governance.openspec_governance_report(root, lifecycle=True)
    assert {
        "openspec_config_json_parse_failed",
        "openspec_list_json_parse_failed",
        "openspec_validate_json_parse_failed",
    } <= set(malformed_report["required_gaps"])


def test_governance_accepts_an_empty_official_change_list(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    monkeypatch.setattr(cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        governance, "protected_branch_active_change_report", lambda *_a, **_k: _residue()
    )

    def run_empty(_root, _base, args):
        if args[:2] == ("config", "list"):
            return _receipt(payload={})
        if args[:1] == ("doctor",):
            return _receipt(payload={"root": {"healthy": True}})
        if args[:1] == ("list",):
            return _receipt(payload={"changes": []})
        if args[:1] == ("validate",):
            return _receipt(payload={"summary": {"totals": {"failed": 0}}})
        raise AssertionError(args)

    monkeypatch.setattr(cli, "run_json", run_empty)

    report = governance.openspec_governance_report(root)

    assert (report["verdict"], report["change"], report["required_gaps"]) == (
        "pass",
        None,
        [],
    )
    assert report["commands"]["status"] == {}


def test_governance_observes_archive_effect_separately_from_generation_scope(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    archive_scope = {
        "verdict": "pass",
        "state": "post_archive_closeout",
        "changes": [{"name": "archived", "path": "openspec/changes/archive/archived"}],
        "required_gaps": [],
    }
    monkeypatch.setattr(cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        governance, "protected_branch_active_change_report", lambda *_a, **_k: _residue()
    )

    def run_empty(_root, _base, args):
        if args[:2] == ("config", "list"):
            return _receipt(payload={})
        if args[:1] == ("doctor",):
            return _receipt(payload={"root": {"healthy": True}})
        if args[:1] == ("list",):
            return _receipt(payload={"changes": []})
        if args[:1] == ("validate",):
            return _receipt(payload={"summary": {"totals": {"failed": 0}}})
        raise AssertionError(args)

    monkeypatch.setattr(cli, "run_json", run_empty)

    def observe_archive(_root, **kwargs):
        assert kwargs["changed_paths"] == ()
        assert kwargs["requested_change"] == "archived"
        return archive_scope

    monkeypatch.setattr(governance, "lease_bound_archive_scope_report", observe_archive)

    report = governance.openspec_governance_report(
        root,
        change="archived",
        lifecycle=True,
        changed_paths=("src/current-generation.py",),
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["change"] == "archived"
    assert report["lifecycle"]["scope_binding"] == archive_scope


def test_governance_reports_invalid_commitment_and_artifact_paths(monkeypatch, tmp_path):
    root = _repo(tmp_path)
    monkeypatch.setattr(
        governance, "protected_branch_active_change_report", lambda *_a, **_k: _residue()
    )
    monkeypatch.setattr(
        governance,
        "official_change_rows",
        lambda _payload: [{"name": "active", "status": "in-progress"}],
    )
    monkeypatch.setattr(governance, "selected_change", lambda *_a, **_k: "active")
    monkeypatch.setattr(governance, "openspec_command_gaps", lambda **_kwargs: [])
    monkeypatch.setattr(
        governance,
        "lifecycle_report",
        lambda *_a, **_k: {
            "required_gaps": [],
            "changes": [],
            "scope_binding": {},
            "protected_branch_residue": _residue(),
        },
    )
    monkeypatch.setattr(cli, "status_contract_gaps", lambda _payload: [])
    monkeypatch.setattr(cli, "instructions_contract_gaps", lambda *_a, **_k: [])
    monkeypatch.setattr(
        governance,
        "load_openspec_commitment",
        lambda *_a, **_k: (_ for _ in ()).throw(ValueError("invalid")),
    )
    monkeypatch.setattr(cli, "run_json", lambda *_a, **_k: _receipt())

    monkeypatch.setattr(cli, "openspec_base_command", lambda: ("openspec",))
    report = governance.openspec_governance_report(root, lifecycle=True)

    assert "commitment_invalid:active" in report["required_gaps"]
    outside = tmp_path / "outside.md"
    status = {
        "artifactPaths": {
            "ignored": "not-a-mapping",
            "mixed": {
                "existingOutputPaths": [
                    root / "openspec/changes/active/specs/capability/spec.md",
                    outside,
                ]
            },
        }
    }
    assert governance.artifact_output_paths(root, {}) == ()
    assert governance.artifact_output_paths(root, status) == (
        "openspec/changes/active/specs/capability/spec.md",
    )
