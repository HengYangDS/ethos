"""Tracked-carrier ownership closure."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import tools.ci.format_selection as format_selection
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[2]


def test_packaged_agent_guidance_is_selected_by_native_markdown_lint() -> None:
    """A new shipped Markdown resource cannot sit outside the executed lint scope."""
    config = yaml.safe_load(
        (ROOT / ".config/checks/markdown/.markdownlint-cli2.yaml").read_text(encoding="utf-8")
    )
    path = ROOT / "src/ethos/data/skills/ethos-repository-work/SKILL.md"
    assert any(path in ROOT.glob(pattern) for pattern in config["globs"])


@pytest.fixture(scope="module")
def carrier_report():
    return json.loads(
        subprocess.check_output(
            (sys.executable, "tools/ci/format_selection.py"),
            cwd=ROOT,
            text=True,
        )
    )


def test_format_selection_receipt_exposes_owner_for_every_tracked_file(carrier_report) -> None:
    payload = carrier_report
    assert payload["verdict"] == "pass"
    assert payload["tracked_file_count"] == len(payload["assignments"])
    assert not any(
        payload[key]
        for key in ("unowned_file_count", "multiply_owned_file_count", "unverified_file_count")
    )
    fields = (
        "format_owner",
        "format_check",
        "validation_owner",
        "validation_command",
        "mutation_policy",
    )
    assert all(entry[field] for entry in payload["assignments"] for field in fields)


def test_current_openspec_markdown_has_generic_and_semantic_validation(carrier_report) -> None:
    assignments = {entry["path"]: entry for entry in carrier_report["assignments"]}
    selected = {"openspec/config.yaml", "openspec/specs/quality/spec.md"}
    selected.update(path for path in assignments if Path(path).match("openspec/changes/*/tasks.md"))
    for relative in sorted(selected):
        assignment = assignments[relative]
        assert assignment["format_owner"] == "official-openspec"
        assert assignment["validation_owner"] == "official-openspec"
        assert assignment["validation_command"] == "ethos prove --gate openspec --json"
        assert assignment["semantic_companions"]


def test_immutable_markdown_is_linted_without_rewrite_authority(carrier_report) -> None:
    assignments = carrier_report["assignments"]
    immutable = [
        entry
        for entry in assignments
        if entry["path"].startswith("openspec/changes/archive/") and entry["path"].endswith(".md")
    ]

    assert immutable
    assert {entry["mutation_policy"] for entry in immutable} == {"forbidden"}
    assert {entry["format_owner"] for entry in immutable} == {"immutable-carrier"}
    assert {entry["validation_owner"] for entry in immutable} == {"markdownlint-cli2"}


def test_native_carriers_separate_canonicalization_from_validation(carrier_report) -> None:
    assignments = {entry["path"]: entry for entry in carrier_report["assignments"]}

    expected = {
        "src/ethos/cli.py": ("ruff", "ruff"),
        "pyproject.toml": ("taplo", "taplo"),
        ".github/workflows/ci.yml": ("cue", "cue"),
        "distributions/npm/bin/ethos.mjs": ("prettier", "prettier"),
        "tools/ci/scripts/bootstrap-python.sh": ("shfmt", "shellcheck"),
        "assets/brand/ethos-logo.svg": ("svgo", "svgo"),
        "assets/brand/ethos-logo-1024.png": ("source-binary", "pillow"),
        ".gitattributes": ("repository-canonical-text", "repository-hygiene"),
        ".config/checks/pytest/pytest.toml": ("taplo", "taplo"),
        "uv.lock": ("uv", "uv"),
    }
    for path, owners in expected.items():
        assignment = assignments[path]
        assert (assignment["format_owner"], assignment["validation_owner"]) == owners
    assert all("," not in entry["format_check"] for entry in assignments.values())
    assert assignments[".config/checks/pytest/pytest.toml"]["validation_command"].endswith(
        "-s config_quality"
    )


@pytest.mark.parametrize(
    ("home", "allowed"),
    [("src/ethos/adapters/", True), ("distributions/npm/", True), ("src/ethos/domain/", False)],
)
def test_native_javascript_transport_uses_its_semantic_adapter_home(
    tmp_path, monkeypatch, capsys, home, allowed
):
    root = init_git_repo(tmp_path / "repo")
    relative = ".config/checks/format/selection.toml"
    config = root / relative
    config.parent.mkdir(parents=True)
    config.write_bytes((ROOT / relative).read_bytes())
    module = root / home / "example.mjs"
    module.parent.mkdir(parents=True)
    module.write_text("export {};\n")
    git(root, "add", relative, str(module.relative_to(root)))
    monkeypatch.setattr(format_selection, "ROOT", root)
    monkeypatch.setattr(format_selection, "CONFIG_PATH", config)
    assert format_selection.main() == (0 if allowed else 1)
    report = json.loads(capsys.readouterr().out)
    assert [item["path"] for item in report["failures"]] == (
        [] if allowed else [home + "example.mjs"]
    )
    assert all(
        item["reason"] == "format outside declared carrier home: .mjs"
        for item in report["failures"]
    )
