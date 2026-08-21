"""Public OpenSpec repository audit failure and unknown reports."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

import ethos.repository.openspec.audit as audit
from ethos.contracts.branch.roles import ROLE_ACCEPTED_ROOT
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _protected_policy(monkeypatch) -> None:
    policy = BranchRolePolicy(release_branch="release")
    monkeypatch.setattr(audit, "load_branch_role_policy", lambda _root: policy)


def test_official_config_reports_malformed_unavailable_and_invalid_shapes(monkeypatch, tmp_path):
    config = tmp_path / "openspec/config.yaml"
    _write(config, "schema: [unterminated\n")
    malformed = audit.official_config_report(tmp_path)
    assert malformed["verdict"] == "block"
    assert malformed["required_gaps"] == ["openspec_config_invalid:ParserError"]

    monkeypatch.setattr(
        audit,
        "_load_official_config",
        lambda _path: (_ for _ in ()).throw(OSError("unavailable")),
    )
    unavailable = audit.official_config_report(tmp_path)
    assert unavailable == {
        "verdict": "unknown",
        "path": config.as_posix(),
        "required_gaps": ["openspec_config_unavailable:OSError"],
    }

    monkeypatch.undo()
    config.write_text("[]\n", encoding="utf-8")
    invalid = audit.official_config_report(tmp_path)
    assert invalid["required_gaps"] == [
        "openspec_config_not_mapping",
        "openspec_config_schema_missing",
    ]


def test_official_config_reports_legacy_and_forbidden_global_store(tmp_path):
    _write(
        tmp_path / "openspec/config.yaml",
        "schema: spec-driven\ndefaultStore: global\nproject: old\nversion: 1\n",
    )

    report = audit.official_config_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "openspec_config_default_store_forbidden",
        "openspec_config_legacy_key:project",
        "openspec_config_legacy_key:version",
    ]


def test_active_change_reports_ignore_archives_and_reject_invalid_identifiers(tmp_path):
    for name in ("valid-change", "20260810-invalid", "archive"):
        (tmp_path / "openspec/changes" / name).mkdir(parents=True)

    assert audit.active_change_names(tmp_path / "openspec") == [
        "20260810-invalid",
        "valid-change",
    ]
    assert audit.active_change_identifier_violations(tmp_path / "openspec") == [
        "openspec_active_change_identifier_invalid:20260810-invalid"
    ]
    assert audit.active_change_names(tmp_path / "absent") == []


def test_protected_branch_report_preserves_unknown_and_unreadable_observations(
    monkeypatch, tmp_path
):
    _protected_policy(monkeypatch)
    observations: dict[str, tuple[dict[str, object], dict[str, object] | None]] = {
        "release": (
            {"verdict": "unknown", "state": "unknown", "required_gaps": ["release-unavailable"]},
            None,
        ),
        "candidate/dev": (
            {"verdict": "pass", "state": "present", "required_gaps": []},
            {"verdict": "unknown", "changes": [], "required_gaps": ["tree-unavailable"]},
        ),
    }

    report = audit.protected_branch_active_change_report(
        tmp_path,
        current_branch="dev",
        branch_observations=observations,
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["release-unavailable", "tree-unavailable"]
    assert report["records"] == []


def test_protected_branch_report_deduplicates_and_promotes_selected_roles(monkeypatch, tmp_path):
    _protected_policy(monkeypatch)
    present: dict[str, object] = {"verdict": "pass", "state": "present", "required_gaps": []}
    observations: dict[str, tuple[dict[str, object], dict[str, object] | None]] = {
        "release": (
            present,
            {"verdict": "pass", "changes": ["active", "active"], "required_gaps": []},
        ),
        "candidate/dev": (present, {"verdict": "pass", "changes": ["active"], "required_gaps": []}),
    }

    report = audit.protected_branch_active_change_report(
        tmp_path, current_branch="dev", branch_observations=observations
    )
    release_only = audit.protected_branch_active_change_required_gaps(report)
    candidate_only = audit.protected_branch_active_change_required_gaps(report, roles={"candidate"})

    assert report["summary"] == {"residue_count": 2}
    assert len(release_only) == 1
    assert ":release:release_root:active" in release_only[0]
    assert len(candidate_only) == 1
    assert ":candidate/dev:candidate:active" in candidate_only[0]


def test_active_change_paths_and_role_reports_cover_unknown_archive_and_unprotected(tmp_path):
    assert audit.active_change_names_from_paths("candidate/dev", None) == {
        "verdict": "unknown",
        "ref": "candidate/dev",
        "changes": [],
        "required_gaps": ["openspec_ref_tree_unavailable:candidate/dev"],
    }
    paths = (
        "README.md",
        "openspec/changes/archive/2026-change/proposal.md",
        "openspec/changes/active/proposal.md",
        "openspec/changes/active/specs/capability/spec.md",
    )
    assert audit.active_change_names_from_paths("candidate/dev", paths)["changes"] == ["active"]
    (tmp_path / "openspec/changes/active").mkdir(parents=True)
    assert audit.active_change_violations_for_role(tmp_path / "openspec", "work-lane") == []
    assert audit.active_change_violations_for_role(tmp_path / "openspec", ROLE_ACCEPTED_ROOT) == [
        "openspec_active_change_unarchived:active:accepted_root"
    ]


def test_removed_spec_obligations_report_only_semantic_lines():
    diff = (
        "--- a/openspec/specs/capability/spec.md\n"
        "+++ b/openspec/specs/capability/spec.md\n"
        "-ordinary prose\n"
        "-**WHEN** input arrives\n"
        "-**THEN** output is emitted\n"
        "+replacement"
    )

    assert audit.changed_openspec_spec_obligation_removal_gaps(None) == [
        "openspec_spec_obligation_diff_unavailable"
    ]
    assert audit.changed_openspec_spec_obligation_removal_gaps(diff) == [
        "openspec_spec_obligation_removed:openspec/specs/capability/spec.md:**WHEN** input arrives",
        (
            "openspec_spec_obligation_removed:openspec/specs/capability/spec.md:"
            "**THEN** output is emitted"
        ),
    ]


def test_shape_report_exposes_non_directory_symlinks_and_missing_specs(monkeypatch, tmp_path):
    specs = tmp_path / "openspec/specs"
    specs.mkdir(parents=True)
    _write(specs / "README.md")
    _write(specs / "unexpected.txt")
    (specs / "missing").mkdir()
    (specs / "mixed").mkdir()
    _write(specs / "mixed/spec.md")
    _write(specs / "mixed/extra.md")
    (specs / "linked").symlink_to(specs / "mixed", target_is_directory=True)

    _write(tmp_path / "openspec/config.yaml", "schema: spec-driven\n")
    monkeypatch.setattr(
        audit,
        "load_branch_role_policy",
        lambda _root: type("Policy", (), {"role_for_branch": lambda *_args: "work_lane"})(),
    )
    residue: dict[str, object] = {
        "verdict": "pass",
        "advisory_gaps": [],
        "required_gaps": [],
    }
    gaps = cast(
        "list[str]",
        audit.openspec_shape_report(
            tmp_path,
            current_branch="work/change",
            protected_branch_residue=residue,
            spec_diff="",
        )["required_gaps"],
    )

    assert set(gaps) == {
        "openspec_specs_root_entry_unexpected:linked",
        "openspec_specs_root_entry_unexpected:unexpected.txt",
        "openspec_spec_capability_spec_missing:missing",
        "openspec_spec_capability_entry_unexpected:mixed:extra.md",
    }
    absent = tmp_path / "absent"
    _write(absent / "openspec/config.yaml", "schema: spec-driven\n")
    (absent / "openspec/specs").write_text("not a directory", encoding="utf-8")
    absent_gaps = cast(
        "list[str]",
        audit.openspec_shape_report(
            absent,
            current_branch="work/change",
            protected_branch_residue=residue,
            spec_diff="",
        )["required_gaps"],
    )
    assert "openspec_specs_not_directory" in absent_gaps
