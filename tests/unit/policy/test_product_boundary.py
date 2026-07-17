from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy.boundary import product as boundary
from tests.support import write_text as _write

if TYPE_CHECKING:
    from pathlib import Path


def term_from_parts(*parts: str) -> str:
    return "".join(parts)


def _workspace(root: Path, body: str) -> None:
    _write(root / ".ethos" / "workspace.toml", body)


def test_product_boundary_reports_clean_minimal_surface(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# ETHOS\n")

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is True
    assert report["state"] == "clean"
    assert report["summary"]["scanned_file_count"] == 1
    assert report["findings"] == []
    assert report["policy"]["product_surfaces"]


def test_product_boundary_reports_literal_leaks_and_sorts_counts(tmp_path: Path) -> None:
    identity_text = term_from_parts("Owner One <owner@", "real.invalid>\n")
    _write(tmp_path / "README.md", identity_text)
    phase_text = term_from_parts("cur", "rent", "/", "fu", "ture", "\n")
    _write(tmp_path / "docs" / "governance" / "phase.md", phase_text)
    local_path = term_from_parts("/", "Users", "/person/project\n")
    _write(tmp_path / "docs" / "governance" / "local.md", local_path)

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is False
    by_kind = report["summary"]["by_kind"]
    assert by_kind["personal_identity_literal"] == 2
    assert by_kind["generic_current_future_phase"] == 1
    assert by_kind["local_workstation_path"] == 1
    assert all(":" in gap for gap in report["required_gaps"])


def test_product_boundary_ignores_local_ethos_state(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# ETHOS\n")
    _write(
        tmp_path / ".ethos" / "state" / "proof" / "head.json",
        term_from_parts("runner=/", "Users", "/person/project/.venv/bin/python\n"),
    )

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is True
    assert report["findings"] == []
    assert report["summary"]["scanned_file_count"] == 1


def test_product_boundary_reports_release_visible_historical_leaks(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# ETHOS\n")
    _write(
        tmp_path / "evidence" / "chronicle" / "topic" / "2026-07-09.md",
        term_from_parts(
            "Command ran from /",
            "Users",
            "/person/private-repo.\n",
            "Evidence used --adopter named-adopter.\n",
        ),
    )
    _write(
        tmp_path / "openspec" / "changes" / "archive" / "2026-07-09-private-adopter" / "tasks.md",
        "The beta-suite reference repository is not release-neutral.\n",
    )

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is False
    assert report["summary"]["scanned_file_count"] == 1
    assert report["summary"]["release_visible_historical_scanned_file_count"] == 2
    by_kind = report["summary"]["by_kind"]
    assert by_kind["archival_local_workstation_path"] == 1
    assert by_kind["archival_adopter_specific_literal"] == 1
    assert by_kind["archival_private_reference_literal"] >= 1
    assert "release_visible_historical_boundary" in report["policy"]


def test_product_boundary_reports_private_domain_marker_in_release_history(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "README.md", "# ETHOS\n")
    marker_text = term_from_parts("d", "mgr", "/domain mechanism comparison\n")
    _write(
        tmp_path / "openspec" / "changes" / "archive" / "2026-07-09-closeout" / "proposal.md",
        marker_text,
    )

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is False
    assert report["summary"]["by_kind"]["archival_private_domain_marker_literal"] == 1


def test_release_visible_historical_filter_handles_skipped_state_cache_and_file_prefix(
    tmp_path: Path, monkeypatch
) -> None:
    _write(tmp_path / ".ethos" / "state" / "proof" / "local.md", "local\n")
    _write(tmp_path / "evidence" / "__pycache__" / "ignored.md", "cache\n")

    assert (
        boundary._is_text_release_visible_historical_file(
            tmp_path / ".ethos" / "state" / "proof" / "local.md", root=tmp_path
        )
        is False
    )
    assert (
        boundary._is_text_release_visible_historical_file(
            tmp_path / "evidence" / "__pycache__" / "ignored.md", root=tmp_path
        )
        is False
    )

    monkeypatch.setattr(boundary, "RELEASE_VISIBLE_HISTORICAL_SURFACE_PREFIXES", ("archive.md",))
    _write(tmp_path / "archive.md", "archival /" + "Users" + "/person/project\n")

    assert boundary.release_visible_historical_files(tmp_path) == [tmp_path / "archive.md"]


def test_product_surface_file_filter_handles_historical_and_binary_paths(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "history" / "old.md", "historical\n")
    _write(
        tmp_path / ".ethos" / "state" / "proof" / "local.json",
        "/" + "Users/person/project\n",
    )
    _write(tmp_path / "README.bin", "binary-ish\n")
    binary = tmp_path / "docs" / "governance" / "bad.md"
    binary.parent.mkdir(parents=True, exist_ok=True)
    binary.write_bytes(b"\xff\xfe")

    assert (
        boundary._is_text_product_file(tmp_path / "docs" / "history" / "old.md", root=tmp_path)
        is False
    )
    cache_file = tmp_path / "packages" / "ethos" / "__pycache__" / "module.py"
    nested_cache_file = tmp_path / "packages" / "ethos" / "src" / "__pycache__" / "skip.py"
    _write(cache_file, "cache\n")
    _write(nested_cache_file, "private\n")

    assert boundary._is_text_product_file(nested_cache_file, root=tmp_path) is False
    assert boundary._is_text_product_file(tmp_path / "README.bin", root=tmp_path) is False
    assert boundary._is_text_product_file(cache_file, root=tmp_path) is False
    assert (
        boundary._is_text_product_file(
            tmp_path / ".ethos" / "state" / "proof" / "local.json", root=tmp_path
        )
        is False
    )
    assert boundary._line_findings(binary, "docs/governance/bad.md", []) == []
    assert boundary.product_boundary_report(tmp_path)["summary"]["scanned_file_count"] == 1


def test_product_boundary_skips_local_ethos_state_proof_records(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "# ETHOS\n")
    _write(
        tmp_path / ".ethos" / "state" / "proof" / ("a" * 40 + ".json"),
        '{"source_root": "/' + "Users" + '/person/projects/ethos"}\n',
    )

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is True
    assert report["state"] == "clean"
    assert report["summary"]["scanned_file_count"] == 1
    assert report["findings"] == []


def test_product_boundary_reports_package_metadata_person_attribution(tmp_path: Path) -> None:
    _write(tmp_path / "package.json", '{"name":"x","author":"One Person"}\n')
    _write(
        tmp_path / "packages" / "ethos" / "pyproject.toml",
        '[project]\nname = "ethos"\nversion = "0"\nauthors = [{name = "One Person"}]\n',
    )
    _write(
        tmp_path / "distributions" / "npm" / "package.json",
        (
            '{"name":"x","contributors":["One Person"],'
            '"files":["bin/ethos.mjs","README.md"],'
            '"bin":{"ethos":"bin/ethos.mjs"}}\n'
        ),
    )

    report = boundary.product_boundary_report(tmp_path)

    gaps = "\n".join(report["required_gaps"])
    assert "single_author_metadata" in gaps
    assert "person_attribution_metadata" in gaps
    assert any(finding["detail"] == "contributors" for finding in report["findings"])
    assert report["summary"]["by_kind"] == {
        "single_author_metadata": 1,
        "person_attribution_metadata": 2,
    }


def test_product_boundary_reports_distribution_manifest_scope_leaks(tmp_path: Path) -> None:
    _write(
        tmp_path / "package.json",
        '{"name":"workspace","workspaces":["distributions/npm"]}\n',
    )
    _write(
        tmp_path / "distributions" / "npm" / "package.json",
        (
            '{"name":"@example/ethos",'
            '"files":["bin/ethos.mjs","README.md","evidence/private.json","tests/",'
            '"lib/index.js"]}\n'
        ),
    )

    report = boundary.product_boundary_report(tmp_path)

    gaps = "\n".join(report["required_gaps"])
    assert "root_workspace_package_publishable" in gaps
    assert "distribution_file_scope_leak" in gaps
    assert report["summary"]["by_kind"] == {
        "root_workspace_package_publishable": 1,
        "distribution_bin_missing": 1,
        "distribution_file_scope_leak": 3,
    }


def test_product_boundary_accepts_neutral_distribution_manifest(tmp_path: Path) -> None:
    _write(
        tmp_path / "package.json",
        '{"name":"workspace","private":true,"workspaces":["distributions/npm"]}\n',
    )
    _write(
        tmp_path / "distributions" / "npm" / "package.json",
        (
            '{"name":"@example/ethos",'
            '"files":["bin/ethos.mjs","README.md"],'
            '"bin":{"ethos":"bin/ethos.mjs"}}\n'
        ),
    )

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is True
    assert report["policy"]["distribution_manifest_files"]
    assert "distribution packages stay enterprise-neutral" in report["policy"]["boundary"]


def test_distribution_manifest_helpers_ignore_malformed_payloads(tmp_path: Path) -> None:
    manifest = tmp_path / "distributions" / "npm" / "package.json"
    _write(manifest, "{")

    assert (
        boundary._npm_distribution_manifest_findings(manifest, "distributions/npm/package.json")
        == []
    )

    _write(manifest, '["not", "object"]')
    assert (
        boundary._npm_distribution_manifest_findings(manifest, "distributions/npm/package.json")
        == []
    )


def test_distribution_manifest_requires_explicit_file_allowlist(tmp_path: Path) -> None:
    manifest = tmp_path / "distributions" / "npm" / "package.json"
    _write(manifest, '{"name":"@example/ethos","bin":{"ethos":"bin/ethos.mjs"}}\n')

    findings = boundary._npm_distribution_manifest_findings(
        manifest, "distributions/npm/package.json"
    )

    assert [finding.to_dict() for finding in findings] == [
        {
            "path": "distributions/npm/package.json",
            "line": 1,
            "kind": "distribution_files_allowlist_missing",
            "detail": "files must be explicit",
        }
    ]


def test_product_boundary_reports_session_authority_literals(tmp_path: Path) -> None:
    session_text = term_from_parts("cur", "rent", " ", "cha", "t", " ", "instru", "ction", "\n")
    _write(tmp_path / "docs" / "decisions" / "accepted" / "DR.md", session_text)

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is False
    assert report["findings"] == [
        {
            "path": "docs/decisions/accepted/DR.md",
            "line": 1,
            "kind": "session_authority_literal",
            "detail": (
                "\\b(?:current\\s+)?chat instruction\\b|"
                "\\bcurrent "
                "migration instruction\\b|\\bcha"
                "t session\\b"
            ),
        }
    ]


def test_product_boundary_reports_named_external_reference_as_active_leak(
    tmp_path: Path,
) -> None:
    roadmap = (
        "This compares the acme-lab reference repository with ETHOS.\n"
        "Compared with `acme-lab`, ETHOS keeps only generic mechanisms.\n"
        "This rule was adopted from acme-lab module-layout study.\n"
        "The acme-lab mechanism comparison snapshot should not be active truth.\n"
        "The matrix says acme-lab has broad helper commands.\n"
        "The beta-suite reference checkout is a mechanism source.\n"
        "The current alpha / beta-suite / ETHOS mechanism comparison is active.\n"
        "Future changes can see which alpha and beta-suite mechanisms were absorbed.\n"
        "| alpha | `alpha reference checkout` | mechanism source |\n"
        "| Mechanism family | alpha has | ETHOS has now |\n"
    )
    _write(tmp_path / "docs" / "plans" / "roadmap.md", roadmap)

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is False
    assert report["summary"]["by_kind"] == {"private_reference_literal": 11}
    assert {finding["kind"] for finding in report["findings"]} == {"private_reference_literal"}
    assert {finding["line"] for finding in report["findings"]} >= {1, 2, 3, 4, 6, 7, 8, 9, 10}


def test_product_boundary_allows_generic_reference_adopter_language(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs" / "plans" / "roadmap.md",
        "Generic reference-adopter governance patterns may remain profile fixtures.\n",
    )

    report = boundary.product_boundary_report(tmp_path)

    assert report["ok"] is True
    assert report["findings"] == []
    assert "private_reference_boundary" in report["policy"]


def test_contributor_policy_reports_clean_multi_actor_policy(tmp_path: Path) -> None:
    _workspace(
        tmp_path,
        "[commit_policy]\n"
        'identity_mode = "external"\n'
        "[[commit_policy.allowed_identities]]\n"
        'role = "team"\n'
        'name = "Platform Team"\n'
        'email = "platform@example.invalid"\n'
        "[[commit_policy.allowed_identities]]\n"
        'role = "service"\n'
        'name = "Build Service"\n'
        'email = "build@example.invalid"\n',
    )

    report = boundary.contributor_policy_report(tmp_path)

    assert report["ok"] is True
    assert report["state"] == "clean"
    assert report["summary"]["roles"] == ["service", "team"]
    assert report["policy"]["identity_model"] == "external_role_policy"
    assert "git_author" in report["policy"]["distinct_identity_facts"]
    assert "adopter_side_owner" in report["policy"]["distinct_identity_facts"]
    assert report["policy"]["allowed_roles"] == sorted(boundary.ALLOWED_IDENTITY_ROLES)


def test_contributor_policy_reports_missing_malformed_and_legacy_policy(tmp_path: Path) -> None:
    _workspace(tmp_path, '[commit_policy]\nexpected_name = "One Person"\n')

    report = boundary.contributor_policy_report(tmp_path)

    gaps = "\n".join(report["required_gaps"])
    assert "single_author_policy" in gaps
    assert "identity_mode_missing" in gaps
    assert "allowed_identities_missing" in gaps

    _workspace(tmp_path, "[commit_policy\n")
    parse_report = boundary.contributor_policy_report(tmp_path)
    assert parse_report["required_gaps"] == [
        "commit_policy_toml_invalid:.ethos/workspace.toml:1",
        "identity_mode_missing:.ethos/workspace.toml:1",
        "allowed_identities_missing:.ethos/workspace.toml:1",
    ]


def test_contributor_policy_reports_role_and_identity_gaps(tmp_path: Path) -> None:
    _workspace(
        tmp_path,
        "[commit_policy]\n"
        'identity_mode = "allowlist"\n'
        "[[commit_policy.allowed_identities]]\n"
        'role = "observer"\n'
        'name = "<your-name-or-team>"\n'
        'email = "person@' + 'real.invalid"\n'
        "[[commit_policy.allowed_identities]]\n"
        'role = "reviewer"\n'
        'name = "Reviewer"\n'
        'email = "reviewer@example.invalid"\n',
    )

    report = boundary.contributor_policy_report(tmp_path)

    gaps = "\n".join(report["required_gaps"])
    assert "identity_mode_not_external" in gaps
    assert "maintainer_or_team_missing" in gaps
    assert "automation_identity_missing" in gaps
    assert "identity_role_unknown" in gaps
    assert "identity_placeholder" in gaps
    assert "personal_identity_literal" in gaps


def test_commit_policy_loader_handles_missing_non_table_and_non_list_entries(
    tmp_path: Path,
) -> None:
    assert boundary.load_workspace_commit_policy(tmp_path) == {}
    _workspace(tmp_path, 'commit_policy = "not a table"\n')
    assert boundary.load_workspace_commit_policy(tmp_path) == {}
    raw = {
        "allowed_identities": [
            "bad",
            {"role": "bot", "name": "Bot", "email": "bot@example.invalid"},
        ]
    }
    assert boundary._identity_entries(raw) == [
        {"role": "bot", "name": "Bot", "email": "bot@example.invalid"}
    ]
    assert boundary._identity_entries({"allowed_identities": "bad"}) == []


def test_finding_serialization() -> None:
    finding = boundary.Finding("README.md", 3, "kind", "detail")

    assert finding.code() == "kind:README.md:3"
    assert finding.to_dict() == {
        "path": "README.md",
        "line": 3,
        "kind": "kind",
        "detail": "detail",
    }


def test_package_metadata_helpers_ignore_malformed_and_non_project_payloads(
    tmp_path: Path,
) -> None:
    bad_json = tmp_path / "package.json"
    _write(bad_json, "{")
    assert boundary._json_package_metadata_findings(bad_json, "package.json") == []

    list_json = tmp_path / "list.json"
    _write(list_json, '["not", "object"]')
    assert boundary._json_package_metadata_findings(list_json, "list.json") == []

    bad_toml = tmp_path / "pyproject.toml"
    _write(bad_toml, "[project")
    assert boundary._toml_package_metadata_findings(bad_toml, "pyproject.toml") == []

    no_project = tmp_path / "no-project.toml"
    _write(no_project, '[tool.example]\nname = "x"\n')
    assert boundary._toml_package_metadata_findings(no_project, "no-project.toml") == []


def test_toml_package_metadata_reports_maintainers(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    _write(
        pyproject,
        '[project]\nname = "ethos"\nversion = "0"\nmaintainers = [{name = "Team"}]\n',
    )

    findings = boundary._toml_package_metadata_findings(pyproject, "pyproject.toml")

    assert [finding.to_dict() for finding in findings] == [
        {
            "path": "pyproject.toml",
            "line": 1,
            "kind": "person_attribution_metadata",
            "detail": "project.maintainers",
        }
    ]
