"""Compose one native Node attempt with its own c8 measurement and evidence custody."""

from __future__ import annotations

import hashlib
import json
import subprocess
from contextlib import ExitStack
from pathlib import Path
from stat import S_ISREG
from time import monotonic
from typing import TYPE_CHECKING
from urllib.parse import unquote
from urllib.parse import urlparse

from ethos.adapters.gates.javascript.execution import command_observation
from ethos.adapters.gates.javascript.execution import native_recipe
from ethos.adapters.gates.javascript.execution import retain_attempt
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.repository.policy.quality_reports import istanbul_coverage_report
from ethos.repository.policy.quality_reports import node_event_report
from ethos.repository.policy.quality_reports import validate_node_precise_coverage

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution
    from ethos.repository.policy.code_subjects import CodeSubject


def _raw_identity(raw: Path, *, validate: bool = False) -> dict[str, str]:
    """Observe only regular attempt-owned native inputs, not filename-shaped authenticity."""
    identities = {}
    for path in sorted(raw.iterdir()):
        if not S_ISREG(path.lstat().st_mode):
            message = "javascript_native_coverage_input_invalid"
            raise ValueError(message)
        content = path.read_bytes()
        if validate:
            validate_node_precise_coverage(content)
        identities[path.name] = hashlib.sha256(content).hexdigest()
    return identities


def _observe_test(
    root: Path,
    command: tuple[str, ...],
    tests: tuple[str, ...],
    raw: Path,
    environment: dict[str, str],
    removed: tuple[str, ...],
    observed: dict[str, object],
    timeout: float = 600,
) -> list[str]:
    """Retain one native journal and its diagnostics independently of coverage success."""
    tested = run_command(
        root,
        command,
        timeout=timeout,
        env={
            **environment,
            "NODE_V8_COVERAGE": str(raw),
            "NODE_OPTIONS": (
                f"--test-reporter={json.dumps(str(Path(__file__).with_name('reporter.mjs')))} "
                f"--test-reporter-destination={json.dumps(str(raw.parent / 'journal.jsonl'))}"
            ),
        },
        remove_env=removed,
        remove_env_prefixes=("MISE_",),
    )
    observed.update(
        test_execution={"argv": command, "exit_code": tested.returncode},
        stdout=tested.stdout,
        stderr=tested.stderr,
        exit_code=tested.returncode,
    )
    return _test_result(root, raw.parent, tests, observed)


def _test_result(
    root: Path, output: Path, tests: tuple[str, ...], observed: dict[str, object]
) -> list[str]:
    """Use the retained test journal, not a launcher's summary, as native scope evidence."""
    journal = output / "journal.jsonl"
    try:
        if not journal.is_file() or journal.is_symlink():
            return ["javascript_native_events_incomplete"]
        payload = journal.read_text(encoding="utf-8")
        counts, diagnostics = node_event_report(root, payload, tests)
    except ValueError as error:
        return [str(error)]
    observed.update(tests=counts, diagnostics=diagnostics, journal=payload)
    gaps = []
    if observed["exit_code"] or counts["failures"] or counts["errors"] or not counts["passed"]:
        gaps.append("javascript_tests_failed")
    if observed["stderr"] or diagnostics:
        gaps.append("javascript_native_diagnostics")
    return gaps


def _observe_execution(
    root: Path,
    execution: NativeExecution,
    command: tuple[str, ...],
    tests: tuple[str, ...],
    output: Path,
    environment: dict[str, str],
    removed: tuple[str, ...],
    observed: dict[str, object],
    timeout: float,
) -> list[str]:
    """Reuse a captured outer test or start one prerequisite after observed non-test work."""
    observed["outer_execution"] = {
        "argv": execution.argv,
        "exit_code": execution.exit_code,
        "stdout": execution.stdout,
        "stderr": execution.stderr,
    }
    journal = output / "journal.jsonl"
    if journal.is_file() and journal.stat().st_size:
        observed.update(
            test_execution={"argv": execution.argv, "exit_code": execution.exit_code},
            stdout=execution.stdout,
            stderr=execution.stderr,
            exit_code=execution.exit_code,
        )
        return _test_result(root, output, tests, observed)
    if execution.exit_code or execution.stderr:
        return ["javascript_outer_attempt_failed"]
    identities = _raw_identity(output / "raw", validate=True)
    scripts = (
        script
        for name in identities
        for script in json.loads((output / "raw" / name).read_bytes())["result"]
    )
    if not identities or any(
        script["url"] == "node:test" or "test_runner/" in script["url"] for script in scripts
    ):
        return ["javascript_native_events_incomplete"]
    for path in (output / "raw").iterdir():
        if not S_ISREG(path.lstat().st_mode):
            return ["javascript_native_coverage_input_invalid"]
        path.unlink()
    return _observe_test(
        root, command, tests, output / "raw", environment, removed, observed, timeout=timeout
    )


def _observe_coverage(
    root: Path,
    node: str,
    c8: Path,
    coverage_arguments: tuple[str, ...],
    subjects: tuple[CodeSubject, ...],
    output: Path,
    environment: dict[str, str],
    removed: tuple[str, ...],
    observed: dict[str, object],
    timeout: float = 120,
) -> list[str]:
    """Report exactly the test-owned raw files without starting another collector."""
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    raw, reports = output / "raw", output / "reports"
    selection = run_command(
        root,
        (node, str(Path(__file__).with_name("selection.mjs")), str(c8), *coverage_arguments),
        stdin=json.dumps(production),
        timeout=timeout,
        env=environment,
        remove_env=removed,
        remove_env_prefixes=("MISE_",),
    )
    if selection.returncode or selection.stderr:
        return ["javascript_native_selection_unknown"]
    selected = json.loads(selection.stdout)
    if (
        not isinstance(selected, dict)
        or not isinstance(selected.get("selected_paths"), list)
        or any(path not in production for path in selected["selected_paths"])
        or len(set(selected["selected_paths"])) != len(selected["selected_paths"])
    ):
        return ["javascript_native_selection_invalid"]
    expected = tuple(selected["selected_paths"])
    observed.update(
        native_selection=selected, unselected_paths=sorted(set(production) - set(expected))
    )
    try:
        before = _raw_identity(raw, validate=True)
    except ValueError as error:
        return [str(error)]
    executed = {
        Path(unquote(urlparse(script["url"]).path)).resolve()
        for name in before
        for script in json.loads((raw / name).read_bytes())["result"]
        if urlparse(script["url"]).scheme == "file"
        and any(
            item["count"] > 0 for function in script["functions"] for item in function["ranges"]
        )
    }
    artifact_runtime = {
        subject.path
        for subject in subjects
        if subject.requires_behavior and not subject.requires_authored_analysis
    }
    executed_artifacts = {path for path in artifact_runtime if (root / path).resolve() in executed}
    observed["executed_generated_paths"] = sorted(executed_artifacts)
    measured = run_command(
        root,
        (
            node,
            str(c8),
            "report",
            *coverage_arguments,
            "--reporter=json-summary",
            "--reporter=json",
            "--check-coverage",
            f"--temp-directory={raw}",
            f"--reports-dir={reports}",
        ),
        timeout=timeout,
        env=environment,
        remove_env=removed,
        remove_env_prefixes=("MISE_",),
    )
    preserved = bool(before) and before == _raw_identity(raw)
    observed.update(
        coverage_execution={"argv": measured.args, "exit_code": measured.returncode},
        coverage_stdout=measured.stdout,
        coverage_stderr=measured.stderr,
        raw_identity=before,
        raw_identity_preserved=preserved,
    )
    gaps = [
        f"javascript_coverage_subject_unselected:{subject.path}"
        for subject in subjects
        if subject.requires_behavior
        and subject.path not in expected
        and subject.path not in executed_artifacts
    ]
    gaps.extend(
        f"javascript_generated_input_unexecuted:{path}"
        for path in sorted(artifact_runtime - executed_artifacts)
    )
    if not preserved:
        gaps.append(
            "javascript_native_coverage_input_changed" if before else "javascript_coverage_missing"
        )
    if measured.returncode or measured.stderr:
        gaps.append("javascript_coverage_failed")
    try:
        coverage, covered = istanbul_coverage_report(
            root, reports / "coverage-summary.json", expected
        )
        observed.update(coverage=coverage, covered_paths=sorted(covered))
        if covered != set(expected):
            gaps.append("javascript_source_unexercised")
    except (OSError, ValueError) as error:
        gaps.append(str(error) if isinstance(error, ValueError) else "javascript_coverage_missing")
    return gaps


def behavior_observation(
    root: Path,
    subjects: tuple[CodeSubject, ...],
    execution: NativeExecution | None,
    node: str,
    native: dict[str, str],
    *,
    timeout_seconds: float | None = None,
) -> dict[str, object]:
    """Test once, measure that raw attempt once, then conserve evidence and retire scratch."""
    deadline = monotonic() + timeout_seconds if timeout_seconds is not None else None
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    production = tuple(subject.path for subject in subjects if subject.requires_behavior)
    if not (root / "package.json").is_file():
        message = "javascript_package_missing"
        raise ValueError(message)
    if not tests or not production:
        message = "javascript_tests_or_sources_missing"
        raise ValueError(message)
    command, coverage_arguments = native_recipe(root, tests, node)
    if execution is not None and execution.node_attempt is None:
        # A generic outer command supplies no owned V8 input. Never invent it or replay tests.
        return {
            "language": "javascript",
            "verdict": "block",
            "required_gaps": ["javascript_native_coverage_custody_unavailable"],
            "stdout": execution.stdout,
            "stderr": execution.stderr,
            "exit_code": execution.exit_code,
        }
    c8 = product_node_module("c8") / "bin/c8.js"
    removed = ("NODE_OPTIONS", "NODE_PATH", "NODE_V8_COVERAGE", "EXPERIMENTAL_MONOCART")
    environment = {key: value for key, value in native.items() if key not in removed}
    with ExitStack() as scope:
        attempt = (
            execution.node_attempt
            if execution is not None
            else scope.enter_context(command_observation(root, command, node))
        )
        if attempt is None:
            message = "javascript_native_coverage_custody_unavailable"
            raise ValueError(message)
        if attempt.root != root.resolve() or Path(attempt.node).resolve() != Path(node).resolve():
            message = "javascript_native_attempt_binding_invalid"
            raise ValueError(message)
        if current_tree(root) != attempt.source_tree:
            message = "javascript_native_attempt_binding_invalid"
            raise ValueError(message)
        output = attempt.output
        raw = output / "raw"
        observed: dict[str, object] = {"language": "javascript", "raw_directory": str(raw)}
        observed["evidence_boundary"] = {
            "claim": "reviewed_native_test_attempt",
            "producer_isolation": "not_provided",
            "structural_validation_is_authentication": False,
        }
        gaps: list[str] = []
        try:
            timeout = max(0, deadline - monotonic()) if deadline else 600
            gaps.extend(
                _observe_execution(
                    root,
                    execution,
                    command,
                    tests,
                    output,
                    environment,
                    removed,
                    observed,
                    timeout,
                )
                if execution is not None
                else _observe_test(
                    root, command, tests, raw, environment, removed, observed, timeout=timeout
                )
            )
            gaps.extend(
                _observe_coverage(
                    root,
                    node,
                    c8,
                    coverage_arguments,
                    subjects,
                    output,
                    environment,
                    removed,
                    observed,
                    timeout=max(0, deadline - monotonic()) if deadline else 120,
                )
            )
        except ProcessExecutionError as error:
            observed["process_failure"] = error.evidence()
            gaps.append(error.code)
        except subprocess.TimeoutExpired as error:
            observed["process_failure"] = {
                "argv": error.cmd,
                "timeout": error.timeout,
                "stdout": error.stdout.decode(errors="replace")
                if isinstance(error.stdout, bytes)
                else error.stdout,
                "stderr": error.stderr.decode(errors="replace")
                if isinstance(error.stderr, bytes)
                else error.stderr,
            }
            gaps.append("javascript_native_attempt_timeout")
        finally:
            if not observed.get("coverage_execution") and not gaps:
                gaps.append("javascript_native_attempt_interrupted")
            observed.update(
                verdict="block" if gaps else "pass", required_gaps=list(dict.fromkeys(gaps))
            )
            observed["artifact"] = retain_attempt(root, output, observed)
    return observed
