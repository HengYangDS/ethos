"""Judge one retained native attempt's reports by quality property, not producer."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.gates.native.python import nox_sessions
from ethos.adapters.gates.native.python import runtime_scopes
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_git
from ethos.repository.policy.gates import gate_execution_identity
from ethos.repository.policy.layout.naming import identifier_naming_findings
from ethos.repository.policy.quality.formats import lcov_files
from ethos.repository.policy.quality.formats import sarif_report
from ethos.repository.policy.quality_reports import coverage_stream_report
from ethos.repository.policy.quality_reports import junit_stream_report

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.adapters.gates.verification import NativeEvidence
    from ethos.adapters.gates.verification import NativeExecution
    from ethos.contracts.gates import NativeOutput
    from ethos.repository.policy.code_subjects import CodeSubject

_COVERAGE = frozenset({"cobertura-xml", "lcov"})


def _custody(
    root: Path, execution: NativeExecution
) -> tuple[NativeEvidence, tuple[CodeSubject, ...]]:
    """Bind the reports to this attempt's command, outputs, exact source and exit status."""
    evidence = execution.evidence
    if evidence is None:
        msg = "native_evidence_unavailable"
        raise ValueError(msg)
    type(evidence.gate).model_validate(evidence.gate.to_dict())
    if evidence.gaps:
        raise ValueError(evidence.gaps[0])
    if execution.cwd != root.resolve() or not evidence.artifact:
        msg = "native_custody_missing"
        raise ValueError(msg)
    expected_argv = tuple(
        item.replace("{native_output}", evidence.output_root) for item in evidence.gate.command[1:]
    )
    if (
        execution.declared_identity != gate_execution_identity(evidence.gate)
        or execution.argv[1:] != expected_argv
        or execution.executable != execution.argv[0]
        or tuple(output for output, _ in evidence.outputs) != evidence.gate.native_outputs
    ):
        msg = "native_selection_invalid"
        raise ValueError(msg)
    tree, subjects = observe_quality_subjects(root, expected_tree=evidence.tree)
    if (
        tree != evidence.tree
        or current_tracked_head(root) != evidence.head
        or tuple(subject.path for subject in subjects) != evidence.subjects
    ):
        msg = "native_source_changed"
        raise ValueError(msg)
    if execution.exit_code != 0:
        msg = "native_execution_failed"
        raise ValueError(msg)
    return evidence, subjects


def _tracked(root: Path, tree: str) -> frozenset[str]:
    """Native reports may name any tracked file; only applicable subjects are claimed."""
    listed = run_git(root, "ls-tree", "-r", "-z", "--name-only", tree, observation=True)
    return frozenset(name for name in listed.stdout.split("\0") if name)


def _outputs(evidence: NativeEvidence, *kinds: str) -> tuple[tuple[NativeOutput, bytes], ...]:
    return tuple(item for item in evidence.outputs if item[0].format in kinds)


def _coverage_files(
    root: Path, output: NativeOutput, content: bytes, tracked: frozenset[str]
) -> dict[str, dict[str, int]]:
    """Read either coverage format as executable and executed lines per tracked file."""
    if output.format == "lcov":
        return lcov_files(content, repository_root=root.resolve(), tracked_paths=tracked)
    report = coverage_stream_report(
        content, include_files=True, repository_root=root.resolve(), source_paths=tuple(tracked)
    )
    return cast("dict[str, dict[str, int]]", report["files"])


def _tests(evidence: NativeEvidence) -> tuple[dict[str, int], set[str]]:
    """Every JUnit report passes with a test case; declared pytest events pair with it."""
    events = {output.sessions[0]: content for output, content in _outputs(evidence, "pytest-jsonl")}
    counts = {"total": 0, "failures": 0, "errors": 0, "skipped": 0}
    tested: set[str] = set()
    for output, content in _outputs(evidence, "junit-xml"):
        paired = events.get(output.sessions[0])
        measured, failed = junit_stream_report(
            content.decode("utf-8"), pytest_events=paired.decode("utf-8") if paired else None
        )
        if failed:
            msg = "native_tests_failed"
            raise ValueError(msg)
        tested.update(output.sessions)
        for key in counts:
            counts[key] += measured[key]
    if not set(events) <= tested:
        msg = "python_native_pytest_scope_invalid"
        raise ValueError(msg)
    return counts, tested


def _behavior(
    root: Path, evidence: NativeEvidence, subjects: tuple[CodeSubject, ...]
) -> tuple[list[str], dict[str, object], dict[str, object]]:
    """Passing tests and executed lines from tested sessions claim the files they ran."""
    coverage = _outputs(evidence, *_COVERAGE)
    if not _outputs(evidence, "junit-xml") or not coverage:
        msg = "native_behavior_missing"
        raise ValueError(msg)
    counts, tested = _tests(evidence)
    if any(not set(output.sessions) <= tested for output, _ in coverage):
        msg = "native_coverage_untested"
        raise ValueError(msg)
    tracked = _tracked(root, evidence.tree)
    measured_files: set[str] = set()
    executed: set[str] = set()
    covered = total = 0
    for output, content in coverage:
        for path, lines in _coverage_files(root, output, content, tracked).items():
            measured_files.add(path)
            covered += lines["hit_lines"]
            total += lines["lines"]
            if lines["hit_lines"] or not lines["lines"]:
                executed.add(path)
    applicable = [subject.path for subject in subjects if subject.requires_behavior]
    unexercised = [path for path in applicable if path in measured_files - executed]
    if unexercised:
        msg = f"native_source_unexercised:{unexercised[0]}"
        raise ValueError(msg)
    claimed = [path for path in applicable if path in executed]
    if not claimed:
        msg = "native_behavior_scope_empty"
        raise ValueError(msg)
    measures: dict[str, object] = {
        "tests": counts,
        "coverage": {
            "covered": covered,
            "total": total,
            "combined_percent": 100 * covered / total if total else 0,
        },
    }
    return claimed, {}, measures


def _static(
    root: Path,
    evidence: NativeEvidence,
    subjects: tuple[CodeSubject, ...],
    scopes: dict[str, frozenset[str]],
) -> tuple[list[str], dict[str, object], dict[str, object]]:
    """Clean SARIF claims the authored files its inventory or its recorded checker read."""
    reports = _outputs(evidence, "sarif")
    if not reports:
        msg = "native_static_missing"
        raise ValueError(msg)
    for subject in subjects:
        if subject.language == "python" and subject.requires_authored_analysis:
            findings = identifier_naming_findings(
                (root / subject.path).read_text(encoding="utf-8"), path=subject.path
            )
            if findings:
                raise ValueError(str(findings[0]["gap"]))
    tracked = _tracked(root, evidence.tree)
    inventory: set[str] = set()
    for output, content in reports:
        report = sarif_report(content, repository_root=root.resolve(), tracked_paths=tracked)
        if report.failures:
            msg = f"native_static_run_failed:{report.failures[0]}"
            raise ValueError(msg)
        if report.findings:
            finding = report.findings[0]
            paths = cast("list[str]", finding["paths"])
            msg = f"native_static_findings:{finding['rule']}:{paths[0] if paths else ''}"
            raise ValueError(msg)
        recorded = scopes.get(output.sessions[0])
        if report.inventory is None and recorded is None:
            msg = f"native_static_scope_unknown:{output.path}"
            raise ValueError(msg)
        inventory.update(report.inventory or ())
        inventory.update(recorded or ())
    authored = [
        subject.path
        for subject in subjects
        if subject.requires_authored_analysis and subject.path in inventory
    ]
    if not authored:
        msg = "native_static_scope_empty"
        raise ValueError(msg)
    # Generated and upstream files owe integrity, not authored analysis.
    artifacts = [subject.path for subject in subjects if not subject.requires_authored_analysis]
    claimed = [subject.path for subject in subjects if subject.path in {*authored, *artifacts}]
    partition: dict[str, object] = (
        {"authored_paths": authored, "artifact_paths": artifacts} if artifacts else {}
    )
    return claimed, partition, {}


def native_report(
    root: Path, execution: NativeExecution, axis: str, *, language: str = ""
) -> dict[str, object]:
    """Consume the sole native attempt; never invoke another test or static tool."""
    evidence, observed = _custody(root, execution)
    sessions = nox_sessions(evidence)
    scopes = runtime_scopes(root, evidence)
    subjects = tuple(
        subject for subject in observed if not language or subject.language == language
    )
    claimed, partition, measures = (
        _behavior(root, evidence, subjects)
        if axis == "behavior"
        else _static(root, evidence, subjects, scopes)
    )
    applicable = [
        subject.path for subject in subjects if axis != "behavior" or subject.requires_behavior
    ]
    unclaimed = [path for path in applicable if path not in claimed]
    return {
        "verdict": "pass",
        "state": "verified",
        "required_gaps": [],
        "native": {
            "declared_identity": list(execution.declared_identity),
            "argv": list(execution.argv),
            "cwd": str(execution.cwd),
            "exit_code": execution.exit_code,
            "stdout": execution.stdout,
            "stderr": execution.stderr,
            "same_attempt": True,
            "artifact": evidence.artifact,
            "sessions": sessions,
            "structural_validation_is_authentication": False,
        },
        "quality_evidence": {
            "axis": axis,
            "source_tree": evidence.tree,
            "selected_paths": claimed,
            **partition,
        },
        **measures,
        **({"unclaimed_paths": unclaimed} if unclaimed else {}),
    }
