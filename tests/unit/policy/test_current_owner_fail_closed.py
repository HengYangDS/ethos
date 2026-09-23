"""Expose unavailable product, carrier and budget observations without false success."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import ethos.domain.source_budget.measurement as source_budget
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.repository.policy.references.closure import product_reference_gaps
from ethos.repository.policy.references.commands import command_executables
from ethos.repository.policy.references.commands import shebang_executable
from ethos.repository.policy.references.commands import shell_executables
from ethos.repository.policy.references.observation import product_references_from_files
from tests.support.governed_repository import git

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
        json.dumps(
            {
                "files": [
                    "bin/ethos.mjs",
                    "./bin/ethos.mjs",
                    "../private",
                    "tests/",
                    "private.txt",
                ],
                "bin": {},
            }
        ),
    )
    _write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "fixture"\nauthors = [{name = "Person"}]\n'
        'maintainers = [{name = "Maintainer"}]\n',
    )
    host_path = f"/{'Users'}/owner/repo\n"
    _write(tmp_path / "openspec/changes/archive/private-change/proposal.md", host_path)
    report = product_boundary_report(tmp_path)
    findings = report["findings"]
    assert isinstance(findings, list)
    kinds = {finding["kind"] for finding in findings}
    assert report["verdict"] == "block"
    assert {
        "single_author_metadata",
        "person_attribution_metadata",
        "root_workspace_package_publishable",
        "distribution_bin_missing",
        "distribution_file_scope_leak",
        "archival_local_workstation_path",
    } <= kinds
    assert {
        finding["detail"]
        for finding in findings
        if finding["kind"] == "distribution_file_scope_leak"
    } == {"../private", "tests/", "private.txt"}


@pytest.mark.parametrize(("package", "project"), [("{", "[project"), ("[]", "project = []")])
def test_unreadable_metadata_does_not_invent_semantic_leak_findings(
    tmp_path: Path, package: str, project: str
) -> None:
    """Native syntax validation owns malformed carriers, not invented leak findings."""
    for relative in ("package.json", "distributions/npm/package.json"):
        _write(tmp_path / relative, package)
    _write(tmp_path / "pyproject.toml", project)
    report = product_boundary_report(tmp_path)
    assert report["findings"] == []
    assert report["required_gaps"] == []


@pytest.mark.parametrize("prefix", ["docs/history", "openspec/changes/archive"])
def test_release_visible_history_checks_paths_and_content(tmp_path: Path, prefix: str) -> None:
    """Both historical surfaces retain path and content provenance checks."""
    relative = f"{prefix}/~" + "/projects/private.md"
    _write(tmp_path / relative, f"/{'Users'}/owner/repo\n")
    report = product_boundary_report(tmp_path)
    observed = report["findings"]
    assert isinstance(observed, list)
    findings = [
        finding for finding in observed if finding["kind"] == "archival_local_workstation_path"
    ]
    assert report["verdict"] == "block"
    assert [finding["path"] for finding in findings] == [relative, relative]
    assert len({finding["detail"] for finding in findings}) == 2


def test_reference_observation_rejects_malformed_carriers_without_inventing_authority() -> None:
    npm_scripts = {
        "verify": {"uv run --frozen python -m pytest", "'unterminated"},
        "cycle": {"npm run cycle"},
    }
    assert shebang_executable("#!'unterminated") == ""
    tokens = ("env", "--unset", "HOME", "TOKEN=value", "--", "npm", "run", "verify")
    executables = command_executables(tokens, npm_scripts)
    assert {"npm", "uv", "python"} <= executables
    tokens = ("npx", "--package", "@scope/tool@1.2.3", "@scope/tool@1.2.3")
    assert command_executables(tokens, {}) == {"npx", "tool"}
    assert command_executables(("npm", "run", "cycle"), npm_scripts) == {"npm"}

    shell = """helper() { ignored-tool; }
VALUES=(one two)
cat <<'EOF'
not-a-command
EOF
env --unset HOME TOKEN=value -- uv run --frozen python -m pytest
helper
"""
    executables = shell_executables(shell, npm_scripts)
    assert {"uv", "python"} <= executables
    assert "helper" not in executables

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
    assert {"python", "bash"} <= observed["executable"]
    assert observed["import"] == {"pytest"}
    assert "printf" not in observed["executable"]
    assert observed["distribution"] == set()
    assert product_reference_gaps(
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
