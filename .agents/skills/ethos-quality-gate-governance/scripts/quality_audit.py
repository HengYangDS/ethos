#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    ".config/ci/scripts/run-python-lint.sh",
    ".config/ci/scripts/run-python-tests.sh",
    ".config/ci/scripts/run-config-lint.sh",
    ".config/ci/scripts/run-shell-lint.sh",
    ".config/ci/scripts/run-docstring-coverage.sh",
    ".config/ci/scripts/run-module-layout.sh",
    ".config/ci/scripts/run-repository-hygiene.sh",
    ".config/checks/coverage/coverage.ini",
    ".config/checks/coverage/policy.toml",
    ".config/checks/docstrings/policy.toml",
    ".config/checks/module-layout/policy.toml",
    ".config/checks/ty/policy.toml",
    ".config/checks/taplo/taplo.toml",
    ".config/checks/yaml/yamllint.yaml",
    ".config/checks/shell/.shellcheckrc",
    "ruff.toml",
    "pytest.ini",
    "system/tools.toml",
)

ACTIVE_CONCERNS = {
    "python_format_lint": ".config/ci/scripts/run-python-lint.sh",
    "tests": ".config/ci/scripts/run-python-tests.sh",
    "python_typing": "ethos quality types --json",
    "coverage": ".config/ci/scripts/run-python-tests.sh",
    "python_docstrings": ".config/ci/scripts/run-docstring-coverage.sh",
    "python_module_layout": ".config/ci/scripts/run-module-layout.sh",
    "toml": ".config/ci/scripts/run-config-lint.sh",
    "yaml": ".config/ci/scripts/run-config-lint.sh",
    "shell": ".config/ci/scripts/run-shell-lint.sh",
    "repository_hygiene": ".config/ci/scripts/run-repository-hygiene.sh",
    "json_syntax": ".config/ci/scripts/run-config-lint.sh",
}


def run_json(root: Path, *args: str) -> dict[str, Any]:
    completed = subprocess.run(
        ["uv", "run", "--group", "dev", "ethos", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return {
            "ok": False,
            "command": ["ethos", *args],
            "required_gaps": [f"command_failed:{' '.join(args)}"],
            "stderr": completed.stderr,
        }
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "command": ["ethos", *args],
            "required_gaps": [f"command_json_invalid:{' '.join(args)}"],
            "error": str(exc),
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
    gaps.extend(_required_file_gaps(root))
    gaps.extend(_active_tool_gaps(root))
    gaps.extend(_pyproject_policy_gaps(root))
    gaps.extend(_coverage_policy_gaps(root))
    gaps.extend(_python_test_runner_gaps(root))
    return gaps


def _required_file_gaps(root: Path) -> list[str]:
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
    if expected_gate.startswith(".config/") and gate != expected_gate:
        gaps.append(f"quality_gate_owner_mismatch:{concern}:{gate or '<missing>'}")
    return gaps


def _pyproject_policy_gaps(root: Path) -> list[str]:
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    forbidden_tool_tables = ("[tool.ruff", "[tool.pytest", "[tool.coverage", "[tool.ty")
    return [
        f"quality_policy_in_pyproject:{marker}"
        for marker in forbidden_tool_tables
        if marker in pyproject
    ]


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
    python_tests = (root / ".config/ci/scripts/run-python-tests.sh").read_text(encoding="utf-8")
    coverage_policy, coverage_policy_gaps = load_toml(root / ".config/checks/coverage/policy.toml")
    hard_floor = coverage_policy.get("current_hard_floor")
    cov_floor_arg = (
        f"--cov-fail-under={hard_floor:g}" if isinstance(hard_floor, (int, float)) else ""
    )
    required_needles = (
        cov_floor_arg,
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


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    type_report = run_json(root, "quality", "types", "--json")
    doc_report = run_json(root, "quality", "docstrings", "--json")
    layout_report = run_json(root, "quality", "module-layout", "--json")
    gaps = owner_gaps(root)
    for report in (type_report, doc_report, layout_report):
        gaps.extend(str(gap) for gap in report.get("required_gaps", []))
    unique_gaps = sorted(dict.fromkeys(gaps))
    payload = {
        "kind": "quality_gate_audit",
        "ok": not unique_gaps,
        "root": str(root),
        "checks": {
            "types": {"ok": bool(type_report.get("ok")), "state": type_report.get("state")},
            "docstrings": {"ok": bool(doc_report.get("ok")), "state": doc_report.get("state")},
            "module_layout": {
                "ok": bool(layout_report.get("ok")),
                "state": layout_report.get("state"),
            },
            "coverage_owner": {
                "ok": not any(gap.startswith("quality_coverage") for gap in owner_gaps(root))
            },
            "owner_shape": {"ok": not owner_gaps(root)},
        },
        "required_gaps": unique_gaps,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
