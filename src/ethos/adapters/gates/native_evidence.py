"""Interpret materials emitted by one already-selected native gate execution."""

from __future__ import annotations

import hashlib
import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ethos.adapters.gates.code_quality import javascript_test_evidence
from ethos.adapters.gates.code_quality import source_subjects
from ethos.adapters.process import run_command
from ethos.contracts.verdict import report_verdict
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from subprocess import CompletedProcess

    from ethos.contracts.gates import Gate


@dataclass(frozen=True, slots=True)
class NativeEvidenceAdapter:
    """One product-owned environment and pure post-execution interpretation."""

    environment: Callable[[Path], Mapping[str, str]]
    observe: Callable[[Path, Path, CompletedProcess[str]], Mapping[str, object]]


def _load(reference: str) -> NativeEvidenceAdapter:
    module_name, _, name = reference.partition(":")
    adapter = getattr(importlib.import_module(module_name), name)
    if not isinstance(adapter, NativeEvidenceAdapter):
        message = f"native_evidence_adapter_invalid:{reference}"
        raise TypeError(message)
    return adapter


def _materials(directory: Path) -> list[dict[str, str]]:
    """Bind interpreter inputs without retaining a second artifact authority."""
    records: list[dict[str, str]] = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink() or (not path.is_dir() and not path.is_file()):
            message = "native_evidence_material_invalid"
            raise ValueError(message)
        if path.is_file():
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            records.append(
                {
                    "path": path.relative_to(directory).as_posix(),
                    "sha256": digest,
                }
            )
    return records


def run_native_gate(
    root: Path, gate: Gate
) -> tuple[CompletedProcess[str], tuple[dict[str, object], ...]]:
    """Execute a declared command once and interpret its owned outputs before cleanup."""
    if not gate.evidence_adapters:
        return run_command(root, gate.command), ()
    adapters = tuple((reference, _load(reference)) for reference in gate.evidence_adapters)
    with TemporaryDirectory(prefix="ethos-gate-evidence-") as temporary:
        directory = Path(temporary)
        environment: dict[str, str] = {}
        for _, adapter in adapters:
            for name, value in adapter.environment(directory).items():
                if name in environment and environment[name] != value:
                    message = f"native_evidence_environment_conflict:{name}"
                    raise ValueError(message)
                environment[name] = value
        completed = run_command(root, gate.command, env=environment)
        materials = _materials(directory)
        reports: list[dict[str, object]] = []
        for reference, adapter in adapters:
            try:
                report = dict(adapter.observe(root, directory, completed))
            except (OSError, TypeError, ValueError) as error:
                report = {
                    "verdict": "block",
                    "required_gaps": [f"native_evidence_unproven:{reference}:{error}"],
                }
            reports.append({"adapter": reference, "report": report, "materials": materials})
        return completed, tuple(reports)


def evidence_gaps(evidence: tuple[dict[str, object], ...]) -> tuple[str, ...]:
    """Keep an unqualified interpreter result from inheriting command success."""
    gaps: list[str] = []
    for item in evidence:
        report = item.get("report")
        if not isinstance(report, dict) or report_verdict(report) != "pass":
            observed = (
                string_sequence(report.get("required_gaps")) if isinstance(report, dict) else []
            )
            gaps.extend(observed or [f"native_evidence_unproven:{item.get('adapter')}"])
    return tuple(dict.fromkeys(gaps))


def _javascript_environment(directory: Path) -> Mapping[str, str]:
    """Ask Node's native test runner to persist JUnit and V8 from the same run."""
    (directory / "v8").mkdir()
    destination = json.dumps(str(directory / "junit.xml"))
    return {
        "NODE_OPTIONS": f"--test-reporter=junit --test-reporter-destination={destination}",
        "NODE_V8_COVERAGE": str(directory / "v8"),
    }


def _javascript_behavior_report(
    root: Path, directory: Path, completed: CompletedProcess[str]
) -> Mapping[str, object]:
    if completed.returncode:
        return {"verdict": "block", "required_gaps": ["native_javascript_tests_failed"]}
    if not (root / "package.json").is_file():
        return {"verdict": "block", "required_gaps": ["javascript_package_missing"]}
    tree, subjects = source_subjects(root)
    selected = tuple(subject for subject in subjects if subject.language == "javascript")
    native = javascript_test_evidence(root, directory / "v8", directory / "junit.xml", selected)
    return {
        "verdict": "pass",
        "native": native,
        "quality_evidence": {
            "axis": "behavior",
            "source_tree": tree,
            "selected_paths": [subject.path for subject in selected if not subject.is_test],
        },
    }


javascript_behavior = NativeEvidenceAdapter(_javascript_environment, _javascript_behavior_report)
