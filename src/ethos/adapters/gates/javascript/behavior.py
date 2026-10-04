"""Run or consume one native Node event stream without replay or discarded diagnostics."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.repository.policy.quality_reports import node_event_report

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution
    from ethos.repository.policy.code_subjects import CodeSubject


def behavior_observation(
    root: Path,
    subjects: tuple[CodeSubject, ...],
    execution: NativeExecution | None,
    node: str,
    native: dict[str, str],
) -> dict[str, object]:
    """Preserve native raw evidence and reject unsupported reuse instead of running again."""
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not (root / "package.json").is_file():
        message = "javascript_package_missing"
        raise ValueError(message)
    if not tests or not production:
        message = "javascript_tests_or_sources_missing"
        raise ValueError(message)
    reporter = Path(__file__).with_name("reporter.mjs")
    command = (
        node,
        "--test",
        "--experimental-test-coverage",
        f"--test-reporter={reporter}",
        "--test-reporter-destination=stdout",
        *tests,
    )
    if execution is None:
        result = run_command(
            root,
            command,
            timeout=300,
            env=native,
            remove_env=("NODE_OPTIONS", "NODE_V8_COVERAGE"),
            remove_env_prefixes=("MISE_",),
        )
        exit_code, stdout, stderr = result.returncode, result.stdout, result.stderr
    else:
        selected = execution.argv
        if not selected:
            message = "javascript_native_test_selection_invalid"
            raise ValueError(message)
        if Path(selected[0]).name in {"mise", "mise.exe"}:
            message = "javascript_native_child_identity_unavailable"
            raise ValueError(message)
        if not selected or execution.cwd != root.resolve() or selected[1:] != command[1:]:
            message = "javascript_native_test_selection_invalid"
            raise ValueError(message)
        executable = execution.executable
        locked = shutil.which("node", path=native["PATH"]) if "PATH" in native else node
        if not executable or locked is None or Path(executable).resolve() != Path(locked).resolve():
            message = "javascript_native_toolchain_unbound"
            raise ValueError(message)
        exit_code, stdout, stderr = execution.exit_code, execution.stdout, execution.stderr
    try:
        counts, observed, diagnostics = node_event_report(root, stdout, tests, production)
    except ValueError as error:
        return {
            "language": "javascript",
            "verdict": "block",
            "required_gaps": [str(error)],
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": exit_code,
        }

    failed = bool(exit_code or stderr or diagnostics)
    return {
        "language": "javascript",
        "verdict": "block" if failed else "pass",
        "tests_passed": counts["total"] - counts["skipped"],
        "covered_paths": sorted(observed),
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "diagnostics": list(diagnostics),
    }
