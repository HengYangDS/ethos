#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    "tools/ci/scripts/run-python-lint.sh",
    "tools/ci/scripts/run-python-tests.sh",
    "tools/ci/scripts/run-config-lint.sh",
    "tools/ci/scripts/run-shell-lint.sh",
    "tools/ci/scripts/run-docstring-coverage.sh",
    "tools/ci/scripts/run-module-layout.sh",
    "tools/ci/scripts/run-repository-hygiene.sh",
    ".config/checks/coverage/coverage.ini",
    ".config/checks/coverage/policy.toml",
    ".config/checks/docstrings/policy.toml",
    ".config/checks/module-layout/policy.toml",
    ".config/checks/ty/policy.toml",
    ".config/checks/ruff/ruff.toml",
    "ruff.toml",
    ".config/checks/pytest/pytest.ini",
    ".config/checks/taplo/taplo.toml",
    ".config/checks/yaml/yamllint.yaml",
    ".config/checks/shell/.shellcheckrc",
    "system/tools.toml",
)

ACTIVE_CONCERNS = {
    "python_format_lint": "tools/ci/scripts/run-python-lint.sh",
    "tests": "tools/ci/scripts/run-python-tests.sh",
    "python_typing": "ethos prove --gate python-types --json",
    "coverage": "tools/ci/scripts/run-python-tests.sh",
    "python_docstrings": "tools/ci/scripts/run-docstring-coverage.sh",
    "python_module_layout": "tools/ci/scripts/run-module-layout.sh",
    "toml": "tools/ci/scripts/run-config-lint.sh",
    "yaml": "tools/ci/scripts/run-config-lint.sh",
    "shell": "tools/ci/scripts/run-shell-lint.sh",
    "repository_hygiene": "tools/ci/scripts/run-repository-hygiene.sh",
    "json_format": "tools/ci/scripts/run-config-lint.sh",
}


def load_toml(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return {}, [f"quality_file_missing:{path.as_posix()}"]
    except tomllib.TOMLDecodeError:
        return {}, [f"quality_toml_invalid:{path.as_posix()}"]


def tool_records(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    payload, gaps = load_toml(root / "system/tools.toml")
    records = payload.get("tool") if isinstance(payload.get("tool"), list) else []
    return [record for record in records if isinstance(record, dict)], gaps


def owner_gaps(root: Path) -> list[str]:
    gaps: list[str] = []
    gaps.extend(required_file_gaps(root))
    gaps.extend(_active_tool_gaps(root))
    gaps.extend(pyproject_policy_gaps(root))
    gaps.extend(_coverage_policy_gaps(root))
    gaps.extend(_python_test_runner_gaps(root))
    gaps.extend(_quality_reference_gaps(root))
    return gaps


def required_file_gaps(root: Path) -> list[str]:
    """Return missing quality-owner carriers for a repository root."""
    return [
        f"quality_owner_missing:{relative}"
        for relative in REQUIRED_FILES
        if not (root / relative).exists()
    ]


def _active_tool_gaps(root: Path) -> list[str]:
    records, gaps = tool_records(root)
    by_concern = {str(record.get("concern") or ""): record for record in records}
    for concern, expected_gate in ACTIVE_CONCERNS.items():
        record = by_concern.get(concern)
        if not record:
            gaps.append(f"quality_tool_record_missing:{concern}")
            continue
        gaps.extend(_tool_gate_gaps(concern, expected_gate, record))
    return gaps


def _tool_gate_gaps(concern: str, expected_gate: str, record: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    if record.get("planned") is True:
        gaps.append(f"quality_active_tool_marked_planned:{concern}")
    gate = str(record.get("gate") or "")
    if gate != expected_gate:
        gaps.append(f"quality_gate_owner_mismatch:{concern}:{gate or '<missing>'}")
    return gaps


def pyproject_policy_gaps(root: Path) -> list[str]:
    """Return quality-policy ownership gaps found in pyproject.toml."""
    pyproject, gaps = load_toml(root / "pyproject.toml")
    if gaps:
        return gaps
    tool = pyproject.get("tool") if isinstance(pyproject.get("tool"), dict) else {}
    if not isinstance(tool, dict):
        return []
    result: list[str] = []
    result.extend(_ruff_pyproject_gaps(tool.get("ruff")))
    result.extend(_pytest_pyproject_gaps(tool.get("pytest")))
    result.extend(
        f"quality_policy_in_pyproject:[tool.{table}"
        for table in ("coverage", "ty")
        if table in tool
    )
    return sorted(result)


def _ruff_pyproject_gaps(raw: object) -> list[str]:
    if raw is None:
        return []
    if raw == {"cache-dir": "build/runtime/tool-cache/ruff"}:
        return []
    if not isinstance(raw, dict):
        return ["quality_policy_in_pyproject:[tool.ruff"]
    return [f"quality_policy_in_pyproject:[tool.ruff].{key}" for key in sorted(raw)]


def _pytest_pyproject_gaps(raw: object) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return ["quality_policy_in_pyproject:[tool.pytest"]
    allowed = {"ini_options": {"cache_dir": "build/runtime/tool-cache/pytest"}}
    if raw == allowed:
        return []
    gaps: list[str] = []
    for key, value in sorted(raw.items()):
        if key != "ini_options":
            gaps.append(f"quality_policy_in_pyproject:[tool.pytest].{key}")
            continue
        if not isinstance(value, dict):
            gaps.append("quality_policy_in_pyproject:[tool.pytest.ini_options]")
            continue
        gaps.extend(
            f"quality_policy_in_pyproject:[tool.pytest.ini_options].{option}"
            for option in sorted(value)
            if option != "cache_dir" or value[option] != "build/runtime/tool-cache/pytest"
        )
    return gaps


def _coverage_policy_gaps(root: Path) -> list[str]:
    gaps: list[str] = []
    coverage_policy, coverage_policy_gaps = load_toml(root / ".config/checks/coverage/policy.toml")
    gaps.extend(coverage_policy_gaps)
    hard_floor = coverage_policy.get("current_hard_floor")
    if not isinstance(hard_floor, (int, float)):
        gaps.append("quality_coverage_floor_missing")
    if coverage_policy.get("branch_coverage_required") is not True:
        gaps.append("quality_branch_coverage_not_required")
    coverage_ini = (root / ".config/checks/coverage/coverage.ini").read_text(encoding="utf-8")
    if isinstance(hard_floor, (int, float)) and f"fail_under = {hard_floor:g}" not in coverage_ini:
        gaps.append(f"quality_coverage_ini_floor_mismatch:{hard_floor:g}")
    if "branch = True" not in coverage_ini:
        gaps.append("quality_coverage_ini_branch_not_true")
    return gaps


def _python_test_runner_gaps(root: Path) -> list[str]:
    python_tests = (root / "tools/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")
    _coverage_policy, coverage_policy_gaps = load_toml(root / ".config/checks/coverage/policy.toml")
    required_needles = (
        "coverage_hard_floor=",
        "--cov-fail-under=${coverage_hard_floor}",
        '--cov-config="${coverage_config_dir}/coverage.ini"',
        '--cov-report="xml:${coverage_evidence_dir}/coverage.xml"',
        'COVERAGE_FILE="${coverage_evidence_dir}/.coverage"',
        "ETHOS_TEST_BASETEMP",
    )
    forbidden_needles = (
        '--cov-config="${coverage_dir}/coverage.ini"',
        '--cov-report="xml:${coverage_dir}/coverage.xml"',
        'COVERAGE_FILE="${coverage_dir}/.coverage"',
        'pytest_tmp_dir="build/runtime/pytest"',
    )
    gaps = coverage_policy_gaps + [
        f"quality_python_tests_missing:{needle}"
        for needle in required_needles
        if needle and needle not in python_tests
    ]
    gaps.extend(
        f"quality_python_tests_forbidden:{needle}"
        for needle in forbidden_needles
        if needle in python_tests
    )
    return gaps


def _quality_reference_gaps(root: Path) -> list[str]:
    reference = (
        root / ".agents/skills/ethos-quality-gate-governance/references/gate-design.md"
    ).read_text(encoding="utf-8")
    gaps: list[str] = []
    if "hard floor is 95 percent" in reference:
        gaps.append("quality_reference_stale_coverage_floor:95")
    if ".config/checks/coverage/policy.toml" not in reference:
        gaps.append("quality_reference_missing_coverage_policy_ssot")
    return gaps


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    gaps = owner_gaps(root)
    unique_gaps = sorted(dict.fromkeys(gaps))
    payload = {
        "kind": "quality_gate_audit",
        "ok": not unique_gaps,
        "root": str(root),
        "checks": {
            "coverage_owner": {"ok": not any(gap.startswith("quality_coverage") for gap in gaps)},
            "owner_shape": {"ok": not gaps},
        },
        "required_gaps": unique_gaps,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
