"""Tracked-carrier ownership closure."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.ci.format_selection import audit

ROOT = Path(__file__).resolve().parents[2]


def test_every_tracked_file_has_one_effective_quality_owner() -> None:
    payload = audit(ROOT)

    assert payload["verdict"] == "pass"
    assert payload["tracked_file_count"] == len(payload["assignments"])
    assert payload["unowned_file_count"] == 0
    assert payload["multiply_owned_file_count"] == 0
    assert payload["unverified_file_count"] == 0


def test_format_selection_receipt_exposes_owner_for_every_tracked_file() -> None:
    completed = subprocess.run(
        (sys.executable, "tools/ci/format_selection.py"),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["tracked_file_count"] == len(payload["assignments"])
    assert all(
        entry["format_owner"]
        and entry["format_check"]
        and entry["validation_owner"]
        and entry["validation_command"]
        and entry["mutation_policy"]
        for entry in payload["assignments"]
    )


def test_current_openspec_markdown_has_generic_and_semantic_validation() -> None:
    assignments = {entry["path"]: entry for entry in audit(ROOT)["assignments"]}
    active_tasks = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "openspec" / "changes").glob("*/tasks.md")
    )

    for relative in (
        "openspec/config.yaml",
        "openspec/specs/quality/spec.md",
        *active_tasks,
    ):
        assignment = assignments[relative]
        assert assignment["format_owner"] == "official-openspec"
        assert assignment["validation_owner"] == "official-openspec"
        assert assignment["validation_command"] == "ethos prove --gate openspec --json"
        assert assignment["semantic_companions"]


def test_immutable_markdown_is_linted_without_rewrite_authority() -> None:
    assignments = audit(ROOT)["assignments"]
    immutable = [
        entry
        for entry in assignments
        if entry["path"].startswith(("evidence/", "openspec/changes/archive/"))
        and entry["path"].endswith(".md")
    ]

    assert immutable
    assert {entry["mutation_policy"] for entry in immutable} == {"forbidden"}
    assert {entry["format_owner"] for entry in immutable} == {"immutable-carrier"}
    assert {entry["validation_owner"] for entry in immutable} == {"markdownlint-cli2"}


def test_native_carriers_separate_canonicalization_from_validation() -> None:
    assignments = {entry["path"]: entry for entry in audit(ROOT)["assignments"]}

    expected = {
        "src/ethos/cli.py": ("ruff", "ruff"),
        "pyproject.toml": ("taplo", "taplo"),
        ".github/workflows/ci.yml": ("prettier", "yamllint"),
        "distributions/npm/bin/ethos.mjs": ("prettier", "prettier"),
        "tools/ci/scripts/bootstrap-python.sh": ("shfmt", "shellcheck"),
        "assets/brand/ethos-logo.svg": ("svgo", "svgo"),
        "assets/brand/ethos-logo-1024.png": ("source-binary", "pillow"),
        "uv.lock": ("uv", "uv"),
    }
    for path, owners in expected.items():
        assignment = assignments[path]
        assert (assignment["format_owner"], assignment["validation_owner"]) == owners


def test_declared_quality_commands_are_executable_owner_surfaces() -> None:
    assignments = audit(ROOT)["assignments"]

    assert all("," not in entry["format_check"] for entry in assignments)
    ini = next(
        entry for entry in assignments if entry["path"] == ".config/checks/pytest/pytest.ini"
    )
    assert ini["validation_owner"] == "tool-native-parser"
    assert ini["validation_command"].endswith("-s config_quality")
