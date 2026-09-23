"""Public OpenSpec repository audit failure and unknown reports."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING
from typing import cast

import pytest
import tomli_w

import ethos.adapters.openspec.configuration as configuration
import ethos.repository.openspec.audit as audit
from ethos.contracts.branch.roles import BranchRolePolicy

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_official_config_reports_malformed_unavailable_and_invalid_shapes(monkeypatch, tmp_path):
    config = tmp_path / "openspec/config.yaml"
    missing = configuration.official_config_report(tmp_path)
    assert missing["verdict"] == "block"
    assert missing["path"] == config.as_posix()
    assert missing["required_gaps"] == ["openspec_config_missing"]
    _write(config, "schema: [unterminated\n")
    malformed = configuration.official_config_report(tmp_path)
    assert malformed["verdict"] == "block"
    assert malformed["required_gaps"] == ["openspec_config_invalid:YAMLParseError"]

    monkeypatch.setattr(
        configuration,
        "run_command",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )
    unavailable = configuration.official_config_report(tmp_path)
    assert unavailable["verdict"] == "unknown"
    assert unavailable["path"] == config.as_posix()
    assert unavailable["required_gaps"] == ["openspec_configuration_observation_unavailable"]

    monkeypatch.undo()
    config.write_text("[]\n", encoding="utf-8")
    invalid = configuration.official_config_report(tmp_path)
    assert invalid["required_gaps"] == [
        "openspec_config_not_mapping",
        "openspec_config_schema_missing",
    ]


@pytest.mark.parametrize("schema", ["schema: spec-driven\n", ""])
def test_official_config_reports_legacy_and_forbidden_global_store(tmp_path, schema):
    _write(
        tmp_path / "openspec/config.yaml",
        schema + "defaultStore: global\nproject: old\nversion: 1\n",
    )

    report = configuration.official_config_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ([] if schema else ["openspec_config_schema_missing"]) + [
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


@pytest.mark.parametrize("release", ["main", "release"])
@pytest.mark.parametrize(
    ("ref_unknown", "tree_unknown", "current"),
    [(True, True, "dev"), (False, False, "dev"), (True, False, "work/current")],
)
def test_governed_branch_report_preserves_partial_knowledge_and_unique_intent(
    tmp_path, release, ref_unknown, tree_unknown, current
):
    """Native branch policy and independent observations preserve known intent amid gaps."""
    _write(
        tmp_path / ".ethos/workspace.toml",
        tomli_w.dumps({"branch_roles": asdict(BranchRolePolicy(release_branch=release))}),
    )
    present = {"verdict": "pass", "state": "present", "required_gaps": []}
    active = {"verdict": "pass", "changes": ["active", "active"], "required_gaps": []}
    ref_gaps = ["release-unavailable"] if ref_unknown else []
    tree_gaps = ["tree-unavailable"] if tree_unknown else []
    observations = {
        release: (
            present | {"verdict": "unknown", "required_gaps": ref_gaps} if ref_unknown else present,
            None if ref_unknown else active,
        ),
        "dev": (present | {"state": "absent"}, None),
        "candidate/dev": (
            present,
            {"verdict": "unknown", "changes": [], "required_gaps": tree_gaps}
            if tree_unknown
            else active,
        ),
    }
    report = audit.governed_branch_intent_report(
        tmp_path, current_branch=current, branch_observations=observations
    )
    records = (
        [] if ref_unknown else [{"branch": release, "role": "release_root", "change": "active"}]
    ) + (
        []
        if tree_unknown
        else [{"branch": "candidate/dev", "role": "candidate", "change": "active"}]
    )
    assert report["verdict"] == ("unknown" if ref_gaps or tree_gaps else "pass")
    assert report["required_gaps"] == ref_gaps + tree_gaps
    assert report["advisory_gaps"] == []
    assert report["records"] == records
    assert report["summary"] == {"change_count": len(records)}


def test_active_change_paths_preserve_unknown_and_exclude_archive():
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
            branch_intent=residue,
            spec_diff="",
            official_config=configuration.official_config_report(tmp_path),
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
            branch_intent=residue,
            spec_diff="",
            official_config=configuration.official_config_report(absent),
        )["required_gaps"],
    )
    assert "openspec_specs_not_directory" in absent_gaps
