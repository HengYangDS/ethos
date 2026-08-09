from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.domain.source_budget.measurement as source_budget
from ethos.repository.openspec.audit import active_change_names_from_paths
from ethos.repository.openspec.audit import changed_openspec_spec_obligation_removal_gaps
from ethos.repository.openspec.audit import official_config_report
from ethos.repository.openspec.audit import protected_branch_active_change_report
from ethos.repository.openspec.audit import protected_branch_active_change_required_gaps
from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.commands import normalize_command
from ethos.repository.policy.references.commands import shebang_executable
from ethos.repository.policy.references.commands import shell_executables
from ethos.repository.policy.references.observation import product_references_from_files
from ethos.repository.policy.references.observation import reference_gaps
from tests.support.governed_repository import git

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_product_boundary_reports_native_metadata_and_identity_failures(tmp_path: Path) -> None:
    _write(
        tmp_path / "package.json",
        json.dumps(
            {
                "author": "Named Person",
                "authors": ["Named Person"],
                "maintainers": ["Named Person"],
                "contributors": ["Named Person"],
                "workspaces": ["packages/*"],
                "private": False,
            }
        ),
    )
    _write(
        tmp_path / "distributions/npm/package.json",
        json.dumps({"files": ["../private", "bin/ethos.mjs"], "bin": {}}),
    )
    _write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "fixture"\nauthors = [{name = "Person"}]\n'
        'maintainers = [{name = "Maintainer"}]\n',
    )
    host_path = f"/{'Users'}/owner/repo\n"
    _write(tmp_path / "openspec/changes/archive/private-change/proposal.md", host_path)
    report = product_boundary_report(tmp_path)
    kinds = {finding["kind"] for finding in report["findings"]}
    assert report["verdict"] == "block"
    assert {
        "single_author_metadata",
        "person_attribution_metadata",
        "root_workspace_package_publishable",
        "distribution_bin_missing",
        "distribution_file_scope_leak",
        "archival_local_workstation_path",
    } <= kinds

    _write(tmp_path / ".ethos/workspace.toml", "[commit_policy\n")
    malformed = contributor_policy_report(tmp_path)
    assert malformed["verdict"] == "block"
    assert malformed["required_gaps"][0].startswith("commit_policy_toml_invalid:")

    _write(
        tmp_path / ".ethos/workspace.toml",
        """[commit_policy]
identity_mode = "personal"
expected_name = "Only One"
allowed_identities = "not-a-list"
""",
    )
    missing = contributor_policy_report(tmp_path)
    assert missing["verdict"] == "block"
    assert {gap.split(":", 1)[0] for gap in missing["required_gaps"]} >= {
        "single_author_policy",
        "identity_mode_not_external",
        "allowed_identities_missing",
    }

    _write(
        tmp_path / ".ethos/workspace.toml",
        """[commit_policy]
identity_mode = "external"

[[commit_policy.allowed_identities]]
role = "unknown"
name = "<your-name-or-team>"
email = "<your-approved-email>"
""",
    )
    invalid_identity = contributor_policy_report(tmp_path)
    identity_kinds = {finding["kind"] for finding in invalid_identity["findings"]}
    assert invalid_identity["verdict"] == "block"
    assert {
        "maintainer_or_team_missing",
        "automation_identity_missing",
        "identity_role_unknown",
        "identity_placeholder",
    } <= identity_kinds


def test_openspec_audit_preserves_unknown_and_blocks_native_shape_loss(tmp_path: Path) -> None:
    missing = official_config_report(tmp_path)
    assert missing == {
        "verdict": "block",
        "path": (tmp_path / "openspec/config.yaml").as_posix(),
        "required_gaps": ["openspec_config_missing"],
    }
    _write(tmp_path / "openspec/config.yaml", "schema: [unterminated\n")
    invalid = official_config_report(tmp_path)
    assert invalid["verdict"] == "block"
    assert invalid["required_gaps"][0].startswith("openspec_config_invalid:")
    _write(tmp_path / "openspec/config.yaml", "defaultStore: legacy\nproject: old\nversion: 1\n")
    legacy = official_config_report(tmp_path)
    assert legacy["verdict"] == "block"
    assert {
        "openspec_config_schema_missing",
        "openspec_config_default_store_forbidden",
        "openspec_config_legacy_key:project",
        "openspec_config_legacy_key:version",
    } <= set(legacy["required_gaps"])

    _write(
        tmp_path / ".ethos/workspace.toml",
        """[branch_roles]
release_branch = "main"
accepted_branch = "dev"
candidate_branch = "candidate/dev"
work_branch_prefix = "work/"
proposal_branch_prefix = "proposal/"
release_mirror = "accepted_ff"
canonical_sibling_worktrees = true
""",
    )
    observations = {
        "main": (
            {"verdict": "unknown", "state": "unknown", "required_gaps": ["main_unreadable"]},
            None,
        ),
        "dev": ({"verdict": "pass", "state": "absent", "required_gaps": []}, None),
        "candidate/dev": (
            {"verdict": "pass", "state": "present", "required_gaps": []},
            {
                "verdict": "pass",
                "changes": ["still-active", "still-active"],
                "required_gaps": [],
            },
        ),
    }
    protected = protected_branch_active_change_report(
        tmp_path, current_branch="work/current", branch_observations=observations
    )
    assert protected["verdict"] == "block"
    assert protected["required_gaps"] == ["main_unreadable"]
    assert protected["summary"] == {"residue_count": 1}
    assert protected_branch_active_change_required_gaps(protected, roles={"candidate"}) == [
        "main_unreadable",
        "openspec_protected_branch_active_change_unarchived:candidate/dev:candidate:still-active",
    ]

    assert active_change_names_from_paths("main", None)["verdict"] == "unknown"
    observed = active_change_names_from_paths(
        "dev",
        (
            "openspec/changes/archive/2026-08-10-old/spec.md",
            "openspec/changes/live/specs/example/spec.md",
            "README.md",
        ),
    )
    assert observed["changes"] == ["live"]
    diff = """--- a/openspec/specs/example/spec.md
+++ b/openspec/specs/example/spec.md
-**WHEN** a governed transition occurs
-ordinary prose
-**THEN** evidence remains exact"""
    assert changed_openspec_spec_obligation_removal_gaps(None) == [
        "openspec_spec_obligation_diff_unavailable"
    ]
    assert changed_openspec_spec_obligation_removal_gaps(diff) == [
        (
            "openspec_spec_obligation_removed:openspec/specs/example/spec.md:"
            "**WHEN** a governed transition occurs"
        ),
        (
            "openspec_spec_obligation_removed:openspec/specs/example/spec.md:"
            "**THEN** evidence remains exact"
        ),
    ]


def test_reference_observation_rejects_malformed_carriers_without_inventing_authority() -> None:
    npm_scripts = {
        "verify": {"uv run --frozen python -m pytest", "'unterminated"},
        "cycle": {"npm run cycle"},
    }
    assert normalize_command("'unterminated") == "'unterminated"
    assert shebang_executable("#!'unterminated") == ""
    executables = command_executables(
        (
            "env",
            "--unset",
            "HOME",
            "TOKEN=value",
            "--",
            "npm",
            "run",
            "verify",
        ),
        npm_scripts,
    )
    assert {"npm", "uv", "python", "pytest"} <= executables
    assert command_executables(
        ("npx", "--package", "@scope/tool@1.2.3", "@scope/tool@1.2.3"), {}
    ) == {
        "npx",
        "tool",
    }
    assert command_executables(("/dev/null",), {}) == set()
    assert command_executables(("npm", "run", "cycle"), npm_scripts) == {"npm"}

    shell = """helper() { ignored-tool; }
VALUES=(one two)
cat <<'EOF'
not-a-command
EOF
env --unset HOME TOKEN=value -- uv run --frozen python -m pytest
helper
"""
    assert {"uv", "python", "pytest"} <= shell_executables(shell, npm_scripts)
    assert "helper" not in shell_executables(shell, npm_scripts)

    observed = product_references_from_files(
        {
            "pyproject.toml": "[project\n",
            "package.json": "not-json",
            ".github/workflows/ci.yml": (
                "jobs:\n  test:\n    steps:\n"
                "      - uses: actions/checkout@v4\n"
                "      - uses: docker://alpine:3\n"
                "      - run: env -- python -m pytest\n"
            ),
            "README.md": "```yaml\ninvalid: [\n```\n`'unterminated`\n",
            "tools/run.sh": "#!/usr/bin/env bash\nprintf ok\n",
        },
        declared_commands=("ethos status",),
    )
    assert {"github", "docker"} <= observed["reference"]
    assert {"python", "pytest", "bash"} <= observed["executable"]
    assert "printf" not in observed["executable"]
    assert observed["distribution"] == set()
    assert reference_gaps(
        {kind: frozenset() for kind in observed},
        observed | {"import": {"ethos", "tests", "tools", "foreign"}},
    ) == [
        "product_reference_not_admitted_at_baseline:import:foreign",
        *[
            f"product_reference_not_admitted_at_baseline:executable:{value}"
            for value in sorted(observed["executable"])
        ],
        *[
            f"product_reference_not_admitted_at_baseline:reference:{value}"
            for value in sorted(observed["reference"])
        ],
    ]


def test_source_budget_public_report_blocks_missing_inventory_and_cross_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert source_budget.source_budget_report(tmp_path)["required_gaps"][0].startswith(
        "source_budget_policy_invalid:"
    )

    selection = tmp_path / ".config/checks/format/selection.toml"
    selection.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / ".config/checks/format/selection.toml", selection)
    rules = tmp_path / ".ethos/rules.toml"
    rules.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / ".ethos/rules.toml", rules)
    unavailable_inventory = source_budget.source_budget_report(tmp_path)
    assert unavailable_inventory["verdict"] == "block"
    assert unavailable_inventory["required_gaps"] == ["source_budget_inventory_unavailable"]

    source = tmp_path / "src/ethos/example.py"
    _write(source, '"""Fixture."""\nVALUE = 1\n')
    git(tmp_path, "init", "-q", "-b", "dev")
    git(tmp_path, "add", ".")
    host_which = source_budget.shutil.which
    monkeypatch.setattr(
        source_budget.shutil,
        "which",
        lambda command, **kwargs: None if command == "scc" else host_which(command, **kwargs),
    )
    missing_cross_check = source_budget.source_budget_report(tmp_path)
    assert missing_cross_check["verdict"] == "block"
    assert "source_budget_scc_unavailable:scc" in missing_cross_check["required_gaps"]
    assert missing_cross_check["metrics"]["python_product"] > 0

    source.write_bytes(b"\xff")
    malformed_source = source_budget.source_budget_report(tmp_path)
    assert malformed_source["verdict"] == "block"
    assert (
        "source_budget_carrier_unreadable:src/ethos/example.py" in malformed_source["required_gaps"]
    )
