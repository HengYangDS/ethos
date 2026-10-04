"""Compose one native Node attempt with its own c8 measurement and evidence custody."""

from __future__ import annotations

import hashlib
import io
import json
import shlex
import subprocess
from pathlib import Path
from stat import S_ISREG
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED
from zipfile import ZipFile

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.adapters.store.content_addressed import write_content_addressed
from ethos.adapters.store.state.schema import local_state_root
from ethos.repository.policy.quality_reports import istanbul_coverage_report
from ethos.repository.policy.quality_reports import node_event_report
from ethos.repository.policy.quality_reports import validate_native_v8_report

if TYPE_CHECKING:
    from ethos.adapters.gates.verification import NativeExecution
    from ethos.repository.policy.code_subjects import CodeSubject


def _native_recipe(
    root: Path, tests: tuple[str, ...], node: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Retain a direct Node recipe; unsupported npm lifecycle is never silently skipped."""
    manifest = json.loads((root / "package.json").read_text(encoding="utf-8"))
    scripts = manifest.get("scripts", {})
    if not isinstance(scripts, dict) or any(key in scripts for key in ("pretest", "posttest")):
        message = "javascript_native_recipe_unsupported"
        raise ValueError(message)
    recipe = scripts.get("test")
    if recipe is None:
        arguments = ("--test", *tests)
    elif isinstance(recipe, str):
        lexer = shlex.shlex(recipe, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        tokens = tuple(lexer)
        if (
            not tokens
            or tokens[0] != "node"
            or tokens.count("--test") != 1
            or any(
                value in {"&&", "||", ";", "|", "&", ">", "<"}
                or any(character in value for character in ("$", "`"))
                or value.startswith(
                    ("--test-reporter", "--experimental-test-coverage", "--test-coverage")
                )
                for value in tokens[1:]
            )
        ):
            message = "javascript_native_recipe_unsupported"
            raise ValueError(message)
        arguments = tokens[1:]
    else:
        message = "javascript_native_recipe_unsupported"
        raise ValueError(message)
    coverage = scripts.get("test:coverage")
    coverage_arguments: tuple[str, ...] = ()
    if coverage is not None:
        lexer = shlex.shlex(coverage, posix=True, punctuation_chars=";&|<>")
        lexer.whitespace_split = True
        tokens = tuple(lexer)
        if (
            any(key in scripts for key in ("pretest:coverage", "posttest:coverage"))
            or len(tokens) < 3
            or tokens[0] != "c8"
            or tokens[-2:] != ("npm", "test")
        ):
            message = "javascript_native_coverage_recipe_unsupported"
            raise ValueError(message)
        coverage_arguments = tokens[1:-2]
    reporter = Path(__file__).with_name("reporter.mjs")
    return (
        node,
        f"--test-reporter={reporter}",
        "--test-reporter-destination=stdout",
        *arguments,
    ), coverage_arguments


def _raw_identity(raw: Path, *, validate: bool = False) -> dict[str, str]:
    """Observe only regular attempt-owned native inputs, not filename-shaped authenticity."""
    identities = {}
    for path in sorted(raw.iterdir()):
        if not S_ISREG(path.lstat().st_mode):
            message = "javascript_native_coverage_input_invalid"
            raise ValueError(message)
        content = path.read_bytes()
        if validate:
            validate_native_v8_report(content)
        identities[path.name] = hashlib.sha256(content).hexdigest()
    return identities


def _retain_attempt(root: Path, output: Path, observation: dict[str, object]) -> dict[str, object]:
    """Conserve raw measurements and adverse output in the existing immutable artifact store."""
    payload = io.BytesIO()
    with ZipFile(payload, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("observation.json", json.dumps(observation, sort_keys=True))
        for path in sorted(output.rglob("*")):
            if S_ISREG(path.lstat().st_mode):
                archive.write(path, path.relative_to(output).as_posix())
    content = payload.getvalue()
    digest = hashlib.sha256(content).hexdigest()
    path = local_state_root(root) / "artifacts" / f"{digest}.zip"
    write_content_addressed(
        path, content, collision="javascript_native_artifact_identity_collision"
    )
    return {
        "path": str(path),
        "sha256": digest,
        "size_bytes": len(content),
        "media_type": "application/zip",
    }


def _observe_test(
    root: Path,
    command: tuple[str, ...],
    tests: tuple[str, ...],
    raw: Path,
    environment: dict[str, str],
    removed: tuple[str, ...],
    observed: dict[str, object],
) -> list[str]:
    """Retain one native journal and its diagnostics independently of coverage success."""
    tested = run_command(
        root,
        command,
        timeout=600,
        env={**environment, "NODE_V8_COVERAGE": str(raw)},
        remove_env=removed,
        remove_env_prefixes=("MISE_",),
    )
    observed.update(
        test_execution={"argv": command, "exit_code": tested.returncode},
        stdout=tested.stdout,
        stderr=tested.stderr,
        exit_code=tested.returncode,
    )
    try:
        counts, diagnostics = node_event_report(root, tested.stdout, tests)
    except ValueError as error:
        return [str(error)]
    observed.update(tests=counts, diagnostics=diagnostics)
    gaps = []
    if tested.returncode or counts["failures"] or counts["errors"] or not counts["passed"]:
        gaps.append("javascript_tests_failed")
    if tested.stderr or diagnostics:
        gaps.append("javascript_native_diagnostics")
    return gaps


def _observe_coverage(
    root: Path,
    node: str,
    c8: Path,
    coverage_arguments: tuple[str, ...],
    production: tuple[str, ...],
    tests: tuple[str, ...],
    output: Path,
    environment: dict[str, str],
    removed: tuple[str, ...],
    observed: dict[str, object],
) -> list[str]:
    """Report exactly the test-owned raw files without starting another collector."""
    raw, reports = output / "raw", output / "reports"
    try:
        before = _raw_identity(raw, validate=True)
    except ValueError as error:
        return [str(error)]
    measured = run_command(
        root,
        (
            node,
            str(c8),
            "report",
            *coverage_arguments,
            "--all",
            *(f"--exclude={path}" for path in tests),
            "--exclude-node-modules=false",
            *(f"--include={path}" for path in production),
            "--reporter=json-summary",
            "--reporter=json",
            "--check-coverage",
            f"--temp-directory={raw}",
            f"--reports-dir={reports}",
        ),
        timeout=120,
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
    gaps = []
    if not preserved:
        gaps.append(
            "javascript_native_coverage_input_changed" if before else "javascript_coverage_missing"
        )
    if measured.returncode or measured.stderr:
        gaps.append("javascript_coverage_failed")
    try:
        coverage, covered = istanbul_coverage_report(
            root, reports / "coverage-summary.json", production
        )
        observed.update(coverage=coverage, covered_paths=sorted(covered))
        if covered != set(production):
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
) -> dict[str, object]:
    """Test once, measure that raw attempt once, then conserve evidence and retire scratch."""
    tests = tuple(subject.path for subject in subjects if subject.is_test)
    production = tuple(subject.path for subject in subjects if not subject.is_test)
    if not (root / "package.json").is_file():
        message = "javascript_package_missing"
        raise ValueError(message)
    if not tests or not production:
        message = "javascript_tests_or_sources_missing"
        raise ValueError(message)
    command, coverage_arguments = _native_recipe(root, tests, node)
    if execution is not None:
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
    with TemporaryDirectory(prefix="ethos-node-") as name:
        output = Path(name)
        raw = output / "raw"
        raw.mkdir()
        observed: dict[str, object] = {"language": "javascript", "raw_directory": str(raw)}
        observed["evidence_boundary"] = {
            "claim": "reviewed_native_test_attempt",
            "producer_isolation": "not_provided",
            "structural_validation_is_authentication": False,
        }
        gaps: list[str] = []
        try:
            gaps.extend(_observe_test(root, command, tests, raw, environment, removed, observed))
            gaps.extend(
                _observe_coverage(
                    root,
                    node,
                    c8,
                    coverage_arguments,
                    production,
                    tests,
                    output,
                    environment,
                    removed,
                    observed,
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
            observed["artifact"] = _retain_attempt(root, output, observed)
    return observed
